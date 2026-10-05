# manga-translator-ui 進入點與執行緒模型

- Scope: shared
- Author: catclaw-ext-merge
- Confidence: [臨]
- Trigger: manga_translator.py, translate_batch, app_logic.py, MangaTranslator 實例化, daemon thread asyncio, desktop_qt_ui/main.py, manga_translator/__main__.py, QThreadPool, 單張圖片 pipeline 順序
- Created-at: 2026-05-14
- Related: module-pipeline-core, module-desktop-qt-ui, pitfall-pyinstaller-dll-order

## 知識

- 單張漫畫圖片的處理 pipeline 依 `manga_translator.py` 定義的順序經過：colorization → upscaling → detection → OCR → textline merge → translation → mask refinement → inpainting → text rendering。
- 批次翻譯的統一入口是 `manga_translator.py:3278` 的 `async def translate_batch(...)`（2026-07-02 時的行號）。
- `MangaTranslator` 類別在 `desktop_qt_ui/app_logic.py` 第 3325 行 import、第 3344 行實例化（2026-07-02 時的行號）。
- 翻譯流程跑在 Python daemon thread 內的 asyncio event loop，由 `app_logic.py` 第 2067 行的 `threading.Thread` 啟動，不是用 Qt 的 `QThreadPool`／`QRunnable`。
- CLI 進入點為 `manga_translator/__main__.py`，GUI 進入點為 `desktop_qt_ui/main.py`，兩個檔案遵守相同的 import 順序規則。
- CLI 翻譯的標準參數為 `--subprocess`、`--batch-per-restart 5`、`--memory-percent 85`、`--use-gpu`、`--format png`、`-v`（2026-05-14 時）。

## 行動

- （依知識內容判斷）
