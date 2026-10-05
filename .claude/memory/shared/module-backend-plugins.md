# module-backend-plugins

- Scope: shared
- Confidence: [臨]
- Trigger: translators, ocr, detection, inpainting, rendering, dispatch, 後端插件, 翻譯器, 檢測器, 嵌字, 渲染
- Tags: L1

## 知識

- **職責**：pipeline 各階段的可插拔後端層——每個子包都是「策略字典 + get/prepare/dispatch/unload 四件套」模式
- **關鍵檔**：
  - `manga_translator/detection/__init__.py` — 檢測分派（`DETECTORS:18`、`dispatch():41`，支援 YOLO-OBB 混合檢測 :63-95；backbones: default/ctd/craft/dbnet_convnext/yolo_obb）
  - `manga_translator/ocr/__init__.py` — OCR 分派（`OCRS:44` 含延遲導入 mocr/paddleocr_vl/openai_ocr/gemini_ocr :21-42、`dispatch():92`）
  - `manga_translator/translators/__init__.py` — 翻譯器分派（`GPT_TRANSLATORS:19`、`TRANSLATORS:29`：openai(_hq)/gemini(_hq)/claude_cli/codex_cli/gemini_cli/sakura；`dispatch():57`、`dispatch_batch():89`）
  - `manga_translator/inpainting/__init__.py` — 修復分派（`INPAINTERS:32`：default=Aot/lama_large/lama_mpe/sd；極端長寬比走 `_dispatch_with_split:157`）
  - `manga_translator/rendering/__init__.py` — 嵌字渲染分派（`dispatch():2107`；openai/gemini renderer 走 `dispatch_api_rendering:2124`）
- **依賴**：`manga_translator/config.py` 的 Enum 決定策略字典 key；`..utils`（TextBlock/Quadrilateral）
- **坑**：渲染座標系 OpenCV=BGR（rendering/__init__.py:1291）；warpPerspective 有 32767 像素限制改局部渲染（:2452）；Lanczos 前須 alpha 預乘（:2492）

## 行動

- 回答此模組問題前，回讀上列關鍵檔取證；新增後端＝在對應策略字典註冊
