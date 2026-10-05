# project-overview

- Scope: shared
- Confidence: [觀]
- Trigger: manga-translator-ui, 漫畫翻譯, manga, 專案總覽, 架構, architecture, 技術棧, tech stack
- Tags: L0

## 知識

- **是什麼**：漫畫圖片自動翻譯桌面應用——PyQt6 GUI + Python pipeline（檢測→OCR→翻譯→修復→嵌字），fork 自 zyddnys/manga-image-translator，本 fork 主要新增 Qt 桌面 UI、可視化編輯器與多平台打包（`_AIDocs/Project_File_Tree.md:120`）
- **技術棧**：Python 3 / PyQt6 / PyTorch 2.8 / onnxruntime 1.20 / numpy >=2.0,<2.3（版本敏感，`CLAUDE.md:18`）；OCR: PaddleOCR/MangaOCR/自訓 CNN；翻譯: OpenAI/Gemini/Sakura/Claude CLI；server: FastAPI；打包: PyInstaller + Docker
- **模組地圖**：
  - `manga_translator/` — 後端核心 pipeline（CLI/Server 入口）→ module-pipeline-core
  - `desktop_qt_ui/` — PyQt6 前端，服務容器 DI 架構 → module-desktop-qt-ui
  - `packaging/` — PyInstaller spec / build scripts / Docker / 自動更新 → module-packaging
  - 後端可插拔子包（detection/ocr/translators/inpainting/rendering）→ module-backend-plugins
  - `doc/` 上游文檔+CHANGELOG；`dict/` `fonts/` `models/` 資源；`requirements_{cpu,gpu,amd,metal}.txt` 多平台鎖檔
- **入口點**：GUI `desktop_qt_ui/main.py:159`（main()，:349 建 MainWindow）；CLI/Server `python -m manga_translator` → `manga_translator/__main__.py:31`（main()，:61 local mode）
- **建置/執行**：macOS `macOS_2_启动Qt界面.sh`、Windows `步骤2-启动Qt界面.bat`、打包 `packaging/build_packages.py`（`CLAUDE.md:28-33`）
- **版本**：`packaging/VERSION` = v2.2.7（_AIDocs 文件寫 v2.2.6 已過時）
- **VCS**：git，origin=github.com/wellstseng/manga-translator-ui，主幹 main；GPL-3.0

## 行動

- 細節問題 → 依模組地圖找對應 L1 atom → 回讀原檔
- 風險分級與技術約束先看 `CLAUDE.md`（中風險以上動工前必讀 _AIDocs 對應段）
