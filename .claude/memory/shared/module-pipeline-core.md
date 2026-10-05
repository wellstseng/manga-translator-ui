# module-pipeline-core

- Scope: shared
- Confidence: [觀]
- Trigger: manga_translator, pipeline, 翻譯流程, translate_batch, 主流程, config, args, 運行模式, mode
- Tags: L1

## 知識

- **職責**：漫畫翻譯核心 pipeline——上色→超分→檢測→OCR→文字行合併→翻譯→遮罩細化→修復→嵌字渲染；支援 local/web/ws/shared 四種模式
- **關鍵檔**：
  - `manga_translator/__main__.py` — CLI 入口（`main():31`，依 mode 分派：web :54 / local :61 / ws :66 / shared :73）
  - `manga_translator/manga_translator.py` — pipeline 主類（`MangaTranslator:345`；單圖入口 `translate():525`；**真正批次協調器 `translate_batch():3278`**；前半段 `_translate_until_translation():4033`、後半段 `_complete_translation_pipeline():5240`；各階段 `_run_detection:1630` `_run_ocr:2289` `_run_inpainting:2997` `_run_text_rendering:3045`）
  - `manga_translator/args.py` — argparse（`create_parser():10`；首參數帶 -i 自動補 local 模式 :132-136）
  - `manga_translator/config.py` — Pydantic 設定模型（頂層 `Config:456` 聚合 8 個子設定；後端列舉 Detector:90 / Ocr:112 / Translator:125）
- **依賴**：torch（裝置選擇 mps/cuda/cpu `manga_translator/manga_translator.py:439-447`）、PyQt6（Qt 離屏渲染）、pydantic、opencv/numpy/shapely
- **坑**：translate_batch 內不可再呼叫 translate()——會無限遞迴（`manga_translator/manga_translator.py:3337` 註解明言）；attempts=-1 是合法值＝無限重試（config.py:381）

## 行動

- 回答此模組問題前，回讀上列關鍵檔取證
