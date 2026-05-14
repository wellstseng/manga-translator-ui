# manga-translator-ui — 專案結構摘要

> 版本：v2.2.6（見 `packaging/VERSION`）
> 原始碼：265 .py（後端）+ 94 .py（Qt UI）+ 17 根目錄檔

---

## 頂層佈局

```
manga-translator-ui/
├── manga_translator/        # 後端核心 pipeline（CLI / Server 入口）
├── desktop_qt_ui/           # PyQt6 桌面 UI（GUI 入口）
├── packaging/               # PyInstaller spec、build scripts、Docker
├── doc/                     # 安裝/使用/API/開發文檔 + 上游 CHANGELOG（30+）
├── dict/                    # 字典資源
├── examples/                # 範例
├── fonts/                   # 字型檔
├── requirements_{cpu,gpu,amd,metal}.txt   # 多平台依賴鎖檔
├── macOS_*.sh / 步骤*.bat   # 安裝/啟動腳本
├── README.md / README_EN.md
└── LICENSE.txt              # GPL-3.0
```

---

## `manga_translator/` — 後端 Pipeline

入口：`__main__.py`（CLI / WebSocket / shared 模式，由 `args.py` 解析）
核心類：`manga_translator.py`

| 子模組 | 職責 |
|--------|------|
| `args.py`, `config.py` | 參數解析、設定載入 |
| `detection/` | 文本區域檢測（CRAFT / CTD / default 三套 backbones） |
| `ocr/` | OCR：32px/48px CNN、MangaOCR、PaddleOCR、PaddleOCR-VL、API OCR |
| `translators/` | OpenAI / Gemini / Sakura / 高品質模式（含 `*_hq.py`） |
| `mask_refinement/` | mask 細修 |
| `inpainting/` | 文字塗除（LDM 等） |
| `upscaling/` | 超解析（Real-CUGAN 等） |
| `colorization/` | 黑白漫上色（v2） |
| `rendering/` | 嵌字渲染：Pillow / HQ / eng 文字、自動斷行、氣泡萃取 |
| `textline_merge/` | 文字行合併 |
| `mode/` | 不同運行模式分派 |
| `server/` | FastAPI 服務（routes / repositories / models / static） |
| `utils/` | 工具（含 `panel/`） |

---

## `desktop_qt_ui/` — PyQt6 前端

入口：`main.py` → `MainWindow`
架構：**服務容器（依賴注入）** — `services/__init__.py:ServiceContainer`

| 子模組 | 職責 |
|--------|------|
| `main_window.py`, `main_view.py`, `editor_view.py` | 主視窗 / 主畫面 / 編輯器畫面 |
| `main_view_parts/` | 主畫面拆分元件 |
| `app_logic.py` | 業務邏輯橋接 |
| `services/` | 服務層：Config / File / History / I18n / Log / OCR / Preset / RenderParameter / State / Translation / Async |
| `editor/` | 可視化編輯器（含 `core/`） |
| `widgets/` | 自訂 widgets（含 themed message box 等） |
| `core/` | UI 核心元件 |
| `utils/` | 版本/資源/輔助工具 |
| `locales/` | i18n 翻譯資源 |
| `theme_registry.py` | 主題註冊 |
| `ruff.toml` | UI 程式碼風格設定 |

---

## `packaging/` — 打包與部署

| 檔案 | 用途 |
|------|------|
| `manga-translator-{cpu,gpu}.spec` | PyInstaller spec（後端） |
| `create-manga-pdfs.spec` | PDF 工具 spec |
| `manga-chapter-splitter.spec` | 章節分頁工具 spec |
| `build_packages.py`, `build_utils/` | 構建腳本 |
| `detect_torch_type.py` | 偵測 GPU 類型自動選 requirements |
| `git_update.py`, `check_version.py` | 自動更新 |
| `Dockerfile`, `docker-compose.yml` | 容器化部署 |
| `pyi_rth_onnxruntime.py` | PyInstaller runtime hook（修 onnxruntime DLL） |
| `launch.py` | 啟動 wrapper |
| `VERSION` | 版本檔（v2.2.6） |

---

## 技術棧

| 類別 | 工具 |
|------|------|
| 語言 | Python 3 |
| UI 框架 | PyQt6 |
| 深度學習 | PyTorch 2.8 / onnxruntime 1.20 / kornia / albumentations |
| OCR | PaddleOCR / PaddleOCR-VL 1.5 / MangaOCR / 自訓 32px/48px CNN |
| 翻譯 | OpenAI (v2.x SDK) / Gemini / Sakura / ctranslate2 |
| 後端 server | FastAPI / aiohttp / aiofiles |
| 影像處理 | OpenCV (contrib) / Pillow / matplotlib |
| 上色 | manga-colorization-v2 |
| 超解析 | Real-CUGAN / MangaJaNai |
| 打包 | PyInstaller（多 spec） / Docker |
| 風格 | ruff（UI 子專案有獨立 ruff.toml） |

---

## 進入點對照

| 場景 | 入口 |
|------|------|
| 桌面 GUI | `desktop_qt_ui/main.py` |
| CLI / Server | `python -m manga_translator` → `manga_translator/__main__.py` |
| macOS 啟動 | `macOS_2_启动Qt界面.sh` |
| Windows 啟動 | `步骤2-启动Qt界面.bat` |
| 打包 | `packaging/build_packages.py` |

---

## 上游關係

Fork 自 [zyddnys/manga-image-translator](https://github.com/zyddnys/manga-image-translator)；本 fork 主要新增 PyQt6 桌面 UI 與可視化編輯器，並客製多平台打包/啟動腳本。
