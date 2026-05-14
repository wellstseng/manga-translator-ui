# manga-translator-ui — 專案導讀 (Claude Code)

> 漫畫圖片自動翻譯桌面應用：PyQt6 GUI + Python pipeline（檢測 / OCR / 翻譯 / 修復 / 嵌字），fork 自 zyddnys/manga-image-translator，多平台打包。

## 風險分級（專案特定）

> 通用分級框架見全域 `~/.claude/CLAUDE.md`。

| 風險等級 | 本專案操作類型 | 驗證要求 |
|---------|--------------|---------|
| **低** | 修文檔、調 i18n 字串、UI 樣式微調 | 直接執行 |
| **中** | 修 `desktop_qt_ui/services/*`、修單一 OCR / translator 實作、改 rendering 參數 | 先讀 `_AIDocs/Project_File_Tree.md` 對應段落 + 目標檔 |
| **高** | 改 pipeline 串接（`manga_translator/manga_translator.py`）、`args.py`/`config.py` schema、服務容器（`services/__init__.py`）注入順序、PyInstaller spec | 必須先讀 _AIDocs 相關文件 + 原始碼 + 上游 `doc/CHANGELOG_v*.md` 對應版本 |
| **極高** | 改 `requirements_*.txt` 主要套件版本、改 `packaging/Dockerfile`、改 onnxruntime / PyTorch 載入邏輯、改多平台啟動腳本 | 必須向使用者確認後才執行 |

## 技術約束

- **Python**：PyTorch 2.8 / onnxruntime 1.20 / numpy >=2.0,<2.3（多套件對 numpy 主版本敏感）
- **UI**：PyQt6（不是 PySide / PyQt5），主執行緒外不能直接動 widget，async 走 `services/async_service.py`
- **多平台依賴鎖檔**：`requirements_cpu.txt` / `_gpu.txt` / `_amd.txt` / `_metal.txt` 內容會分歧，改一個請評估是否要同步其他
- **打包敏感**：onnxruntime / PyTorch DLL 載入在 PyInstaller 環境需 `os.add_dll_directory`（見 `desktop_qt_ui/main.py:24-33`），`packaging/pyi_rth_onnxruntime.py` 為 runtime hook
- **服務容器**：`desktop_qt_ui/services/ServiceContainer` 為依賴注入中樞，新服務必須在 `services/__init__.py` 註冊
- **i18n**：UI 字串走 `services/i18n_service.py`（locales/），不要寫死中文字串
- **GPL-3.0**：衍生程式碼受 GPL-3.0 約束

## 入口

| 場景 | 入口 |
|------|------|
| GUI | `desktop_qt_ui/main.py` |
| CLI / Server | `python -m manga_translator` |
| 啟動腳本 | `macOS_2_启动Qt界面.sh` / `步骤2-启动Qt界面.bat` |
| 打包 | `packaging/build_packages.py` |

## 詳細資訊

- 完整資料夾佈局 / 模組職責 → `_AIDocs/Project_File_Tree.md`
- 變更歷史（AI 文件）→ `_AIDocs/_CHANGELOG.md`
- 上游官方變更記錄 → `doc/CHANGELOG_v*.md`
- 開發者文檔 → `doc/DEVELOPMENT.md`
