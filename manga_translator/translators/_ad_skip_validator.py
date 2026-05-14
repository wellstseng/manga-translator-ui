"""AD_SKIP / LOGO_SKIP 規則違反偵測器。

manga_hq_zh.yaml § 5.b 規定漫畫廣告頁、卷頭/卷末宣傳語不該翻譯。
但 LLM（特別是 codex/gemini）偶爾會忽略此規則直接翻成中文。

本 module 用 regex 偵測「原文有廣告詞 + 譯文也翻成中文版」的違反情境，
回傳違反清單給 translator 用來 retry（並把違反原因加進 prompt 提示）。

由 claude_cli / codex_cli / gemini_cli 共用呼叫，集中規則維護點。
"""
from __future__ import annotations

import re
from typing import List, Tuple

# 日文廣告/宣傳/卷頭卷末特徵詞（OCR 抓到的原文 pattern）
SOURCE_AD_PATTERNS = [
    r"\d+\s*周年",
    r"\d+\s*万部",
    r"累計",
    r"突破",
    r"特別\s*鼎談",
    r"鼎談",
    r"次\s*ページ",
    r"アニメ化",
    r"映画化",
    r"ドラマ\s*CD",
    r"巻末",
    r"巻頭",
    r"続きは",
    r"乞うご期待",
    r"お楽しみに",
    r"次回\s*予告",
    r"インタビュー",
    r"特集",
    r"シリーズ",
]

# 譯文「被誤翻」特徵詞（中文版）
TARGET_AD_PATTERNS = [
    r"\d+\s*週年",
    r"\d+\s*周年",
    r"\d+\s*萬部",
    r"\d+\s*万部",
    r"累計",
    r"鼎談",
    r"三方對談",
    r"下\s*一\s*頁",
    r"次\s*頁",
    r"動畫化",
    r"電影化",
    r"廣播劇",
    r"廣播\s*CD",
    r"卷末",
    r"卷頭",
    r"敬請期待",
    r"請期待",
    r"特別\s*專訪",
    r"專訪",
]

_SRC_RE = [re.compile(p) for p in SOURCE_AD_PATTERNS]
_TGT_RE = [re.compile(p) for p in TARGET_AD_PATTERNS]


def detect_ad_skip_violations(
    source_texts: List[str],
    translations: List[str],
) -> List[Tuple[int, str, str]]:
    """偵測 AD_SKIP 規則違反。

    違反條件：原文含 SOURCE_AD_PATTERNS 任一 + 譯文含 TARGET_AD_PATTERNS 任一
              + 譯文 != 原文（即被翻譯了）。

    回傳：list of (index, source_text, translation)，空 list 表全部通過。
    """
    violations: List[Tuple[int, str, str]] = []
    for i, (src, tgt) in enumerate(zip(source_texts, translations)):
        if not src or not tgt:
            continue
        if src.strip() == tgt.strip():
            # 譯文 = 原文（正確的 AD_SKIP 行為）
            continue
        src_hit = any(rx.search(src) for rx in _SRC_RE)
        if not src_hit:
            continue
        tgt_hit = any(rx.search(tgt) for rx in _TGT_RE)
        if tgt_hit:
            violations.append((i, src, tgt))
    return violations


def format_violations_for_retry(violations: List[Tuple[int, str, str]]) -> str:
    """把違反清單格式化為 retry hint 字串，給 LLM 看下次改正。"""
    if not violations:
        return ""
    lines = ["AD_SKIP 規則違反（廣告/宣傳語不該翻，譯文應保留原文 + note: AD_SKIP）："]
    for idx, src, tgt in violations:
        lines.append(f"  id={idx + 1}: 原文「{src[:40]}」→ 你翻成「{tgt[:40]}」")
    lines.append("→ 下次必須輸出原文（{\"id\": N, \"text\": \"原文\", \"note\": \"AD_SKIP\"}）。")
    return "\n".join(lines)
