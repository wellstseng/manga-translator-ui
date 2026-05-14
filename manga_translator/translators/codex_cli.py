import asyncio
import json
import os
import re
import tempfile
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


def _normalize_to_png_rgb(image, max_size: int = 1024):
    if image.mode == "P":
        image = image.convert("RGBA" if "transparency" in image.info else "RGB")
    if image.mode == "RGBA":
        bg = Image.new('RGB', image.size, (255, 255, 255))
        bg.paste(image, mask=image.split()[-1])
        image = bg
    elif image.mode in ("LA", "L", "1", "CMYK"):
        if image.mode == "LA":
            image = image.convert("RGBA")
            bg = Image.new('RGB', image.size, (255, 255, 255))
            bg.paste(image, mask=image.split()[-1])
            image = bg
        else:
            image = image.convert("RGB")
    elif image.mode != "RGB":
        image = image.convert("RGB")
    w, h = image.size
    if max(w, h) > max_size:
        scale = max_size / max(w, h)
        image = image.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    return image


class CodexCliTranslator(CommonTranslator):
    """Vision-enabled translator backed by `codex exec --json` headless CLI.

    Uses ChatGPT subscription via codex OAuth (no API key billing). Sends the
    manga page image (with bbox numbers drawn) + text list to Codex via
    `-i <file>` flag.

    CLI invocation:
      codex exec [resume <session>] --skip-git-repo-check --json [-m <model>]
                 -i <tmpfile1.png> [-i <tmpfile2.png> ...] "<prompt>"

    NDJSON events:
      - {"type":"thread.started","thread_id":"<uuid>"}  → capture as session id
      - {"type":"item.completed","item":{"type":"agent_message","text":"..."}} → final
      - {"type":"turn.completed"}                        → end
    """

    _LANGUAGE_CODE_MAP = VALID_LANGUAGES

    def __init__(self):
        super().__init__()
        self.prev_context = ""

        is_web_server = os.getenv('MANGA_TRANSLATOR_WEB_SERVER', 'false').lower() == 'true'
        if not is_web_server:
            from dotenv import load_dotenv
            load_dotenv(override=True)

        self.cli_path = os.getenv('CODEX_CLI_PATH', 'codex')
        self.model = os.getenv('CODEX_CLI_MODEL', '').strip() or None
        self.cli_timeout = float(os.getenv('CODEX_CLI_TIMEOUT', '900'))
        self.persistent_session = os.getenv('CODEX_CLI_PERSISTENT_SESSION', '1').strip().lower() in ('1', 'true', 'yes', 'on')
        self.image_max_size = int(os.getenv('CODEX_CLI_IMAGE_MAX_SIZE', '1024'))

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
            self.logger.info(f"Codex CLI max requests per minute: {max_rpm}")

        user_api_model = self._get_config_value(translator_args, 'user_api_model', None)
        if user_api_model:
            self.model = user_api_model
            self.logger.info(f"[CodexCli] Model override: {user_api_model}")

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
            self.logger.info("Codex CLI: no batch_data, using single-image fallback path")
            fallback_regions = getattr(ctx, 'text_regions', []) if ctx else []
            batch_data = [{
                'image': getattr(ctx, 'input', None) if ctx else None,
                'text_regions': fallback_regions if fallback_regions else [],
                'text_order': list(range(1, len(queries) + 1)),
                'upscaled_size': None,
                'original_texts': queries,
            }]

        self.logger.info(
            f"Using Codex CLI translator (vision) for {len(queries)} texts, "
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

        # 把 image 寫到 tempfile，codex 用 -i <file> 附加
        self.logger.info(f"Codex HQ: preparing {len(batch_data)} image batch item(s)")
        image_paths: List[str] = []
        tmp_files: List[str] = []
        try:
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
                    self.logger.debug(f"Drew {len(text_regions)} bbox on image[{img_idx + 1}]")
                image = _normalize_to_png_rgb(image, max_size=self.image_max_size)
                tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False, prefix=f"codex_img_{img_idx}_")
                image.save(tmp.name, format="PNG")
                tmp.close()
                tmp_files.append(tmp.name)
                image_paths.append(tmp.name)

            send_images = len(image_paths) > 0
            self.logger.info(f"Codex HQ: wrote {len(image_paths)} image(s) to tempfile")
            if not send_images:
                self.logger.info("No image available, Codex falls back to text-only")

            return await self._do_translate_loop(
                texts, batch_data, image_paths, send_images,
                source_lang, target_lang, custom_prompt_json,
                line_break_prompt_json, ctx, split_level,
            )
        finally:
            for p in tmp_files:
                try:
                    os.unlink(p)
                except Exception:
                    pass

    async def _do_translate_loop(self, texts, batch_data, image_paths, send_images,
                                  source_lang, target_lang, custom_prompt_json,
                                  line_break_prompt_json, ctx, split_level) -> List[str]:
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
                raise Exception(f"达到最大尝试次数 ({self._max_total_attempts})，最后一次错误: {msg}")

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
                full_prompt = (
                    f"{system_prompt}\n\n---\n\n[Previous translation context]\n"
                    f"{self.prev_context}\n\n---\n\n{user_prompt}"
                )
            else:
                full_prompt = f"{system_prompt}\n\n---\n\n{user_prompt}"

            if self._MAX_REQUESTS_PER_MINUTE > 0:
                await self._ratelimit_sleep()

            try:
                effective_image_paths = image_paths if send_images else []
                result_text, finish_reason = await self._call_codex_cli(full_prompt, effective_image_paths)

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
                        self.logger.warning("Empty 2x with images, next retry strips images")
                        send_images = False
                    await self._sleep_with_cancel_polling(1)
                    continue

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

                self.logger.debug(f"--- Codex CLI Raw Response ---\n{clean}\n------------------------------")

                translations, new_terms = parse_hq_response(clean)

                if extract_glossary and new_terms:
                    self._emit_terms_from_list(new_terms)
                    prompt_path = None
                    if ctx and hasattr(ctx, 'config') and hasattr(ctx.config, 'translator'):
                        prompt_path = getattr(ctx.config.translator, 'high_quality_prompt_path', None)
                    if prompt_path:
                        merge_glossary_to_file(prompt_path, new_terms)
                    else:
                        self.logger.warning("Extracted new terms but prompt path not in context.")

                if len(translations) != len(texts):
                    retry_attempt += 1
                    retry_reason = f"Count mismatch: expected {len(texts)}, got {len(translations)}"
                    log_at = f"{attempt}/{max_retries}" if not is_infinite else f"Attempt {attempt}"
                    self.logger.warning(f"[{log_at}] {retry_reason}")
                    self.logger.warning(f"Expected: {texts}")
                    self.logger.warning(f"Got: {translations}")
                    last_exception = Exception(f"翻译数量不匹配: 期望 {len(texts)} 条，实际 {len(translations)} 条")
                    if not is_infinite and attempt >= max_retries:
                        raise Exception(f"Count mismatch after {max_retries} attempts")
                    self._session_id = None
                    await self._sleep_with_cancel_polling(2)
                    continue

                is_valid, error_msg = self._validate_translation_quality(texts, translations)
                if not is_valid:
                    retry_attempt += 1
                    retry_reason = f"Quality check failed: {error_msg}"
                    log_at = f"{attempt}/{max_retries}" if not is_infinite else f"Attempt {attempt}"
                    self.logger.warning(f"[{log_at}] {retry_reason}")
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
                    self.logger.info(f"Codex HQ: SFX skip 處理 {sfx_skipped} 條（譯文→空字串讓 render 跳過嵌字）")

                self._emit_final_translation_results(texts, translations)

                if not self._validate_br_markers(translations, queries=texts, ctx=ctx,
                                                  batch_data=batch_data, split_level=split_level):
                    retry_attempt += 1
                    retry_reason = "BR markers missing"
                    log_at = f"{attempt}/{max_retries}" if not is_infinite else f"Attempt {attempt}"
                    self.logger.warning(f"[{log_at}] {retry_reason}")
                    last_exception = Exception("AI断句检查失败")
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
            except Exception as e:
                last_exception = e
                log_at = f"{attempt}/{max_retries}" if not is_infinite else f"Attempt {attempt}"
                self.logger.warning(f"Codex CLI error ({log_at}): {e}")
                if not is_infinite and attempt >= max_retries:
                    raise
                self._session_id = None
                await self._sleep_with_cancel_polling(1)

        raise last_exception if last_exception else Exception("Codex CLI failed after retries")

    async def _call_codex_cli(self, prompt: str, image_paths: List[str]) -> Tuple[str, str]:
        """Spawn `codex exec --json` with `-i <file>` for each image, read NDJSON."""
        if self._session_id:
            cmd = [self.cli_path, "exec", "resume", self._session_id, "--skip-git-repo-check", "--json"]
        else:
            cmd = [self.cli_path, "exec", "--skip-git-repo-check", "--json"]
        if self.model:
            cmd.extend(["-m", self.model])
        for p in image_paths:
            cmd.extend(["-i", p])
        # `-i` 是 multi-value flag，後接 prompt 會被 codex CLI 誤吃；用 `--` 強制 disambiguate
        cmd.append("--")
        cmd.append(prompt)

        self.logger.debug(
            f"Spawning Codex CLI (resume={self._session_id}, model={self.model}, "
            f"images={len(image_paths)}, prompt_len={len(prompt)})"
        )

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=8 * 1024 * 1024,
        )

        result_text = ""
        finish_reason: Optional[str] = None
        captured_session_id: Optional[str] = None

        try:
            try:
                while True:
                    line_bytes = await asyncio.wait_for(proc.stdout.readline(), timeout=self.cli_timeout)
                    if not line_bytes:
                        break
                    line = line_bytes.decode('utf-8', errors='replace').strip()
                    if not line:
                        continue
                    try:
                        evt = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    t = evt.get("type")
                    if t == "thread.started":
                        captured_session_id = evt.get("thread_id")
                    elif t == "item.completed":
                        item = evt.get("item", {})
                        if item.get("type") == "agent_message":
                            text = item.get("text", "") or ""
                            if text:
                                result_text = text
                        elif item.get("type") == "error":
                            self.logger.warning(f"Codex item error: {item}")
                            finish_reason = "error"
                    elif t == "turn.completed":
                        if result_text and finish_reason is None:
                            finish_reason = "stop"
                        break
                    elif t == "turn.failed" or t == "error":
                        self.logger.warning(f"Codex event: {evt}")
                        finish_reason = "error"
                        break
            except asyncio.TimeoutError:
                self.logger.error(f"Codex CLI timeout after {self.cli_timeout}s")
                finish_reason = "timeout"

            if captured_session_id and finish_reason == "stop":
                if not self._session_id:
                    self.logger.info(f"[CodexCli] Captured session: {captured_session_id}")
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
                self.logger.debug(f"Cleanup error: {e}")

            if not result_text and finish_reason != "timeout":
                try:
                    err_data = await proc.stderr.read()
                    if err_data:
                        err_str = err_data.decode('utf-8', errors='replace').strip()
                        if err_str:
                            self.logger.warning(f"Codex CLI stderr: {err_str[:800]}")
                except Exception:
                    pass

        return result_text, finish_reason or "exit"
