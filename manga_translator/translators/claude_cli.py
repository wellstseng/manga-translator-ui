import asyncio
import base64
import json
import logging
import os
import re
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image

from ._ad_skip_validator import (
    apply_sfx_skip,
    detect_ad_skip_violations,
    format_violations_for_retry,
)
from .common import (
    VALID_LANGUAGES,
    CommonTranslator,
    draw_text_boxes_on_image,
    merge_glossary_to_file,
    parse_hq_response,
)


def encode_image_to_base64(image, max_size: int = 1024) -> str:
    """Encode PIL Image to base64 PNG (RGB-normalized, optionally downscaled).

    Identical normalization rules to openai_hq.encode_image_for_openai —
    keep visual parity across HQ translators.
    """
    if image.mode == "P":
        image = image.convert("RGBA" if "transparency" in image.info else "RGB")

    if image.mode == "RGBA":
        background = Image.new('RGB', image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[-1])
        image = background
    elif image.mode in ("LA", "L", "1", "CMYK"):
        if image.mode == "LA":
            image = image.convert("RGBA")
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])
            image = background
        else:
            image = image.convert("RGB")
    elif image.mode != "RGB":
        image = image.convert("RGB")

    w, h = image.size
    if max(w, h) > max_size:
        scale = max_size / max(w, h)
        new_w, new_h = int(w * scale), int(h * scale)
        image = image.resize((new_w, new_h), Image.LANCZOS)

    buf = BytesIO()
    image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode('utf-8')


class ClaudeCliRateLimitError(Exception):
    """Claude CLI 訂閱用量達上限。不應 retry，因每次 retry 仍會收同樣 limit 訊息且耗訊息額度。"""


class ClaudeCliTranslator(CommonTranslator):
    """Vision-enabled translator backed by `claude -p` with stdin content array.

    Uses Claude Code subscription (no API key billing). Sends the manga page
    image (with bbox numbers drawn) + text list to Claude — equivalent quality
    path to OpenAIHighQualityTranslator but routed through CLI.

    CLI spec (stdin JSON):
      claude -p --input-format stream-json --output-format stream-json
             --verbose --include-partial-messages --dangerously-skip-permissions
             [--resume <id>] [--model <name>]

    stdin (one JSON per line):
      {"type":"user","message":{"role":"user","content":[
        {"type":"text","text":"<system+user prompt>"},
        {"type":"image","source":{"type":"base64","media_type":"image/png","data":"<b64>"}},
        ...more images...
      ]}}
      then close stdin to end turn.

    stdout NDJSON: same as claude_cli.py — system/init / assistant / result.
    """

    _LANGUAGE_CODE_MAP = VALID_LANGUAGES

    def __init__(self):
        super().__init__()
        self.prev_context = ""

        is_web_server = os.getenv('MANGA_TRANSLATOR_WEB_SERVER', 'false').lower() == 'true'
        if not is_web_server:
            from dotenv import load_dotenv
            load_dotenv(override=True)

        self.cli_path = os.getenv('CLAUDE_CLI_PATH', 'claude')
        self.model = os.getenv('CLAUDE_CLI_MODEL', '').strip() or None
        self.cli_timeout = float(os.getenv('CLAUDE_CLI_TIMEOUT', '900'))
        self.persistent_session = os.getenv('CLAUDE_CLI_PERSISTENT_SESSION', '1').strip().lower() in ('1', 'true', 'yes', 'on')
        self.image_max_size = int(os.getenv('CLAUDE_CLI_IMAGE_MAX_SIZE', '1024'))

        self._session_id: Optional[str] = None
        self._last_session_key: Optional[str] = None
        self._enable_streaming = False

    def set_prev_context(self, context: str):
        self.prev_context = context if context else ""

    def parse_args(self, args):
        super().parse_args(args)
        translator_args = self._resolve_translator_config(args)
        self._max_total_attempts = self._resolve_max_total_attempts()

        max_rpm = self._get_config_value(translator_args, 'max_requests_per_minute', 0)
        if max_rpm > 0:
            self._MAX_REQUESTS_PER_MINUTE = max_rpm
            self.logger.info(f"Claude CLI max requests per minute: {max_rpm}")

        user_api_model = self._get_config_value(translator_args, 'user_api_model', None)
        if user_api_model:
            self.model = user_api_model
            self.logger.info(f"[ClaudeCli] Model override: {user_api_model}")

    def _build_user_prompt(self, batch_data: List[Dict], ctx: Any, retry_attempt: int = 0, retry_reason: str = "") -> str:
        return self._build_user_prompt_for_hq(batch_data, ctx, "", retry_attempt=retry_attempt, retry_reason=retry_reason)

    def _get_system_prompt(self, source_lang: str, target_lang: str, custom_prompt_json: Dict[str, Any] = None,
                          line_break_prompt_json: Dict[str, Any] = None, retry_attempt: int = 0,
                          retry_reason: str = "", extract_glossary: bool = False) -> str:
        return self._build_system_prompt(
            source_lang, target_lang,
            custom_prompt_json=custom_prompt_json,
            line_break_prompt_json=line_break_prompt_json,
            retry_attempt=retry_attempt,
            retry_reason=retry_reason,
            extract_glossary=extract_glossary,
        )

    def _compute_session_key(self, ctx) -> str:
        if not self.persistent_session:
            return f"single-{id(ctx)}"
        if ctx is not None and hasattr(ctx, 'input') and getattr(ctx.input, 'name', None):
            try:
                return os.path.dirname(ctx.input.name) or "global"
            except Exception:
                return "global"
        return "global"

    async def _translate(self, from_lang: str, to_lang: str, queries: List[str], ctx=None) -> List[str]:
        if not queries:
            return []

        self._reset_global_attempt_count()

        batch_data = getattr(ctx, 'high_quality_batch_data', None) if ctx else None
        if not batch_data:
            self.logger.info("Claude CLI: no batch_data provided, using single-image fallback path")
            fallback_regions = getattr(ctx, 'text_regions', []) if ctx else []
            batch_data = [{
                'image': getattr(ctx, 'input', None) if ctx else None,
                'text_regions': fallback_regions if fallback_regions else [],
                'text_order': list(range(1, len(queries) + 1)),
                'upscaled_size': None,
                'original_texts': queries,
            }]

        self.logger.info(
            f"Using Claude CLI translator (vision) for {len(queries)} texts, "
            f"{len(batch_data)} images, max attempts: {self._max_total_attempts}"
        )
        custom_prompt_json = getattr(ctx, 'custom_prompt_json', None)
        line_break_prompt_json = getattr(ctx, 'line_break_prompt_json', None)

        translations = await self._translate_with_split(
            self._translate_batch_high_quality,
            queries,
            split_level=0,
            batch_data=batch_data,
            source_lang=from_lang,
            target_lang=to_lang,
            custom_prompt_json=custom_prompt_json,
            line_break_prompt_json=line_break_prompt_json,
            ctx=ctx,
        )

        translations = [self._clean_translation_output(q, r, to_lang) for q, r in zip(queries, translations)]
        return translations

    async def _translate_batch_high_quality(self, texts: List[str], batch_data: List[Dict],
                                            source_lang: str, target_lang: str,
                                            custom_prompt_json: Dict[str, Any] = None,
                                            line_break_prompt_json: Dict[str, Any] = None,
                                            ctx: Any = None, split_level: int = 0) -> List[str]:
        if not texts:
            return []
        if batch_data is None:
            batch_data = []

        self.logger.info(f"Claude HQ: preparing {len(batch_data)} image batch item(s)")
        image_blocks: List[Dict[str, Any]] = []
        for img_idx, data in enumerate(batch_data):
            image = data.get('image')
            if image is None:
                self.logger.debug(f"Image[{img_idx + 1}] missing, skip")
                continue

            text_regions = data.get('text_regions', [])
            text_order = data.get('text_order', [])
            upscaled_size = data.get('upscaled_size')
            if text_regions and text_order:
                image = draw_text_boxes_on_image(image, text_regions, text_order, upscaled_size)
                self.logger.debug(f"Drew {len(text_regions)} numbered bbox on image[{img_idx + 1}]")

            b64 = encode_image_to_base64(image, max_size=self.image_max_size)
            image_blocks.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": b64,
                },
            })

        send_images = len(image_blocks) > 0
        self.logger.info(f"Claude HQ: encoded {len(image_blocks)} image(s) to base64")
        if not send_images:
            self.logger.info("No image available, Claude HQ falls back to text-only")

        retry_attempt = 0
        retry_reason = ""
        max_retries = self._resolve_max_total_attempts()
        attempt = 0
        is_infinite = max_retries == -1
        last_exception: Optional[Exception] = None

        session_key = self._compute_session_key(ctx)
        if session_key != self._last_session_key:
            self._session_id = None
            self._last_session_key = session_key

        while is_infinite or attempt < max_retries:
            self._check_cancelled()

            if not self._increment_global_attempt():
                msg = str(last_exception) if last_exception else "Unknown error"
                raise Exception(
                    f"达到最大尝试次数 ({self._max_total_attempts})，最后一次错误: {msg}"
                )

            attempt += 1

            config_extract = False
            if ctx and hasattr(ctx, 'config') and hasattr(ctx.config, 'translator'):
                config_extract = getattr(ctx.config.translator, 'extract_glossary', False)
            extract_glossary = bool(custom_prompt_json) and config_extract

            system_prompt = self._get_system_prompt(
                source_lang, target_lang,
                custom_prompt_json=custom_prompt_json,
                line_break_prompt_json=line_break_prompt_json,
                retry_attempt=retry_attempt,
                retry_reason=retry_reason,
                extract_glossary=extract_glossary,
            )
            user_prompt = self._build_user_prompt(
                batch_data, ctx,
                retry_attempt=retry_attempt,
                retry_reason=retry_reason,
            )

            if self.prev_context:
                combined_text = (
                    f"{system_prompt}\n\n---\n\n[Previous translation context]\n"
                    f"{self.prev_context}\n\n---\n\n{user_prompt}"
                )
            else:
                combined_text = f"{system_prompt}\n\n---\n\n{user_prompt}"

            content_blocks: List[Dict[str, Any]] = [{"type": "text", "text": combined_text}]
            if send_images:
                content_blocks.extend(image_blocks)
            elif retry_attempt > 0:
                self.logger.warning("Degraded mode: text-only (images stripped)")

            if self._MAX_REQUESTS_PER_MINUTE > 0:
                await self._ratelimit_sleep()

            try:
                result_text, finish_reason = await self._call_claude_cli(content_blocks)

                if not result_text:
                    retry_attempt += 1
                    retry_reason = f"Empty response (finish_reason: {finish_reason})"
                    last_exception = Exception(retry_reason)
                    log_at = f"{attempt}/{max_retries}" if not is_infinite else f"Attempt {attempt}"
                    self.logger.warning(f"[{log_at}] {retry_reason}")
                    if not is_infinite and attempt >= max_retries:
                        raise last_exception
                    self._session_id = None
                    if send_images and retry_attempt >= 2:
                        self.logger.warning("Empty response twice with images, next retry strips images")
                        send_images = False
                    await self._sleep_with_cancel_polling(1)
                    continue

                # Claude 訂閱 rate limit：CLI 直接回 "You've hit your limit · resets HH:MMam/pm (TZ)"
                # 此訊息不是 JSON，硬 retry 只會白燒額度，丟 ClaudeCliRateLimitError 跳過 retry。
                if "hit your limit" in result_text.lower():
                    self.logger.error(f"Claude CLI 訂閱用量上限觸發，停止 retry：{result_text.strip()[:120]}")
                    raise ClaudeCliRateLimitError(result_text.strip()[:200])

                clean = result_text.strip()
                if clean.startswith("```") and clean.endswith("```"):
                    code_match = re.search(r'```(?:json)?\s*\n(.*?)\n```', clean, flags=re.DOTALL)
                    if code_match:
                        clean = code_match.group(1).strip()
                    else:
                        clean = clean.strip("`").strip()
                clean = re.sub(r'(</think>)?<think>.*?</think>', '', clean, flags=re.DOTALL)
                answer_match = re.search(r'<answer>(.*?)</answer>', clean, flags=re.DOTALL)
                if answer_match:
                    clean = answer_match.group(1).strip()

                self.logger.debug(f"--- Claude CLI Raw Response ---\n{clean}\n----------------------------------")

                translations, new_terms = parse_hq_response(clean)

                if extract_glossary and new_terms:
                    self._emit_terms_from_list(new_terms)
                    prompt_path = None
                    if ctx and hasattr(ctx, 'config') and hasattr(ctx.config, 'translator'):
                        prompt_path = getattr(ctx.config.translator, 'high_quality_prompt_path', None)
                    if prompt_path:
                        merge_glossary_to_file(prompt_path, new_terms)
                    else:
                        self.logger.warning("Extracted new terms but prompt path not found in context.")

                if len(translations) != len(texts):
                    retry_attempt += 1
                    retry_reason = f"Translation count mismatch: expected {len(texts)}, got {len(translations)}"
                    log_at = f"{attempt}/{max_retries}" if not is_infinite else f"Attempt {attempt}"
                    self.logger.warning(f"[{log_at}] {retry_reason}. Retrying...")
                    self.logger.warning(f"Expected texts: {texts}")
                    self.logger.warning(f"Got translations: {translations}")
                    last_exception = Exception(
                        f"翻译数量不匹配: 期望 {len(texts)} 条，实际得到 {len(translations)} 条"
                    )
                    if not is_infinite and attempt >= max_retries:
                        raise Exception(
                            f"Translation count mismatch after {max_retries} attempts: expected {len(texts)}, got {len(translations)}"
                        )
                    self._session_id = None
                    await self._sleep_with_cancel_polling(2)
                    continue

                is_valid, error_msg = self._validate_translation_quality(texts, translations)
                if not is_valid:
                    retry_attempt += 1
                    retry_reason = f"Quality check failed: {error_msg}"
                    log_at = f"{attempt}/{max_retries}" if not is_infinite else f"Attempt {attempt}"
                    self.logger.warning(f"[{log_at}] {retry_reason}. Retrying...")
                    last_exception = Exception(f"翻译质量检查失败: {error_msg}")
                    if not is_infinite and attempt >= max_retries:
                        raise Exception(f"Quality check failed after {max_retries} attempts: {error_msg}")
                    self._session_id = None
                    await self._sleep_with_cancel_polling(2)
                    continue

                ad_violations = detect_ad_skip_violations(texts, translations)
                if ad_violations:
                    retry_attempt += 1
                    retry_reason = format_violations_for_retry(ad_violations)
                    log_at = f"{attempt}/{max_retries}" if not is_infinite else f"Attempt {attempt}"
                    self.logger.warning(f"[{log_at}] AD_SKIP 違反 {len(ad_violations)} 條，retry")
                    last_exception = Exception(f"AD_SKIP 規則違反: {len(ad_violations)} 條")
                    if not is_infinite and attempt >= max_retries:
                        self.logger.warning("AD_SKIP 違反但達 max_retries，放行")
                    else:
                        self._session_id = None
                        await self._sleep_with_cancel_polling(2)
                        continue

                translations, sfx_skipped = apply_sfx_skip(texts, translations)
                if sfx_skipped:
                    self.logger.info(f"Claude HQ: SFX skip 處理 {sfx_skipped} 條（譯文→空字串讓 render 跳過嵌字）")

                self._emit_final_translation_results(texts, translations)

                if not self._validate_br_markers(translations, queries=texts, ctx=ctx,
                                                  batch_data=batch_data, split_level=split_level):
                    retry_attempt += 1
                    retry_reason = "BR markers missing in translations"
                    log_at = f"{attempt}/{max_retries}" if not is_infinite else f"Attempt {attempt}"
                    self.logger.warning(f"[{log_at}] {retry_reason}, retrying...")
                    last_exception = Exception("AI断句检查失败: 翻译结果缺少必要的[BR]标记")
                    if not is_infinite and attempt >= max_retries:
                        from .common import BRMarkersValidationException
                        raise BRMarkersValidationException(
                            missing_count=0,
                            total_count=len(texts),
                            tolerance=max(1, len(texts) // 10),
                        )
                    self._session_id = None
                    await self._sleep_with_cancel_polling(2)
                    continue

                return translations[:len(texts)]

            except asyncio.CancelledError:
                raise
            except ClaudeCliRateLimitError:
                raise
            except Exception as e:
                last_exception = e
                log_at = f"{attempt}/{max_retries}" if not is_infinite else f"Attempt {attempt}"
                self.logger.warning(f"Claude CLI translation error ({log_at}): {e}")
                if not is_infinite and attempt >= max_retries:
                    raise
                self._session_id = None
                await self._sleep_with_cancel_polling(1)

        raise last_exception if last_exception else Exception("Claude CLI translation failed after all retries")

    async def _call_claude_cli(self, content_blocks: List[Dict[str, Any]]) -> Tuple[str, str]:
        """Spawn claude with --input-format stream-json, push one user message via stdin,
        close stdin, then read stdout NDJSON until result event.

        Returns: (result_text, finish_reason)
        """
        cmd = [
            self.cli_path, "-p",
            "--input-format", "stream-json",
            "--output-format", "stream-json",
            "--verbose",
            "--include-partial-messages",
            "--dangerously-skip-permissions",
        ]
        if self._session_id:
            cmd.extend(["--resume", self._session_id])
        if self.model:
            cmd.extend(["--model", self.model])

        n_text = sum(1 for b in content_blocks if b.get("type") == "text")
        n_image = sum(1 for b in content_blocks if b.get("type") == "image")
        self.logger.debug(
            f"Spawning Claude CLI (resume={self._session_id}, model={self.model}, "
            f"text_blocks={n_text}, image_blocks={n_image})"
        )

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=8 * 1024 * 1024,
        )

        user_msg = {
            "type": "user",
            "message": {
                "role": "user",
                "content": content_blocks,
            },
        }

        result_text = ""
        finish_reason: Optional[str] = None
        captured_session_id: Optional[str] = None

        try:
            try:
                proc.stdin.write((json.dumps(user_msg, ensure_ascii=False) + "\n").encode("utf-8"))
                await proc.stdin.drain()
                proc.stdin.close()
            except Exception as e:
                self.logger.warning(f"Failed writing to Claude CLI stdin: {e}")
                finish_reason = "stdin_error"
                return result_text, finish_reason

            try:
                while True:
                    line_bytes = await asyncio.wait_for(
                        proc.stdout.readline(),
                        timeout=self.cli_timeout,
                    )
                    if not line_bytes:
                        break
                    line = line_bytes.decode('utf-8', errors='replace').strip()
                    if not line:
                        continue
                    try:
                        evt = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    evt_type = evt.get("type")
                    if evt_type == "system" and evt.get("subtype") == "init":
                        captured_session_id = evt.get("session_id")
                    elif evt_type == "result":
                        result_text = evt.get("result", "") or ""
                        is_error = evt.get("is_error", False)
                        finish_reason = "error" if is_error else "stop"
                        if is_error:
                            self.logger.warning(
                                f"Claude CLI result is_error=true: {evt.get('subtype', 'unknown')}"
                            )
                        break
            except asyncio.TimeoutError:
                self.logger.error(f"Claude CLI timeout after {self.cli_timeout}s")
                finish_reason = "timeout"

            if captured_session_id and finish_reason == "stop":
                if not self._session_id:
                    self.logger.info(f"[ClaudeCli] Captured session: {captured_session_id}")
                self._session_id = captured_session_id
        finally:
            try:
                if proc.returncode is None:
                    proc.terminate()
                    try:
                        await asyncio.wait_for(proc.wait(), timeout=5)
                    except asyncio.TimeoutError:
                        proc.kill()
                        await proc.wait()
                else:
                    await proc.wait()
            except Exception as e:
                self.logger.debug(f"Subprocess cleanup error: {e}")

            if not result_text and finish_reason != "timeout":
                try:
                    err_data = await proc.stderr.read()
                    if err_data:
                        err_str = err_data.decode('utf-8', errors='replace').strip()
                        if err_str:
                            self.logger.warning(f"Claude CLI stderr: {err_str[:800]}")
                except Exception:
                    pass

        return result_text, finish_reason or "exit"
