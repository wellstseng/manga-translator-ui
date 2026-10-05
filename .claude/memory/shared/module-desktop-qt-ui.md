# module-desktop-qt-ui

- Scope: shared
- Confidence: [觀]
- Trigger: desktop_qt_ui, PyQt6, GUI, 主視窗, MainWindow, 編輯器, editor, ServiceContainer, 服務容器, i18n, async
- Tags: L1

## 知識

- **職責**：PyQt6 桌面前端——參數設定主視圖 + 逐區塊修文/重繪的可視化編輯器；以 ServiceContainer 依賴注入管理服務，在獨立執行緒呼叫後端 pipeline
- **關鍵檔**：
  - `desktop_qt_ui/main.py` — 入口（`main():159`；PyInstaller DLL 段 :24-40；:349 建 MainWindow；結尾 `os._exit` 防 daemon 執行緒卡死 :506）
  - `desktop_qt_ui/services/__init__.py` — DI 容器（`ServiceContainer:27`；註冊順序 essential `:66` log→state→config→i18n→preset、heavy `:93` file→translation→ocr→async→history→render_parameter→resource_manager；`ServiceManager` 單例 :169）
  - `desktop_qt_ui/app_logic.py` — 業務邏輯核心 4282 行（`MainAppLogic:117`；`TranslationWorker:2654` QThread 內 :3663 `await translator.translate_batch()`——**與後端的主呼叫界面**）
  - `desktop_qt_ui/main_window.py` — 主窗殼（`MainWindow:18`；編輯器延遲初始化 `_ensure_editor_initialized:119`）
  - `desktop_qt_ui/editor/editor_controller.py` — 編輯器控制器（`EditorController:34`，inpaint/OCR/翻譯異步協調）
  - `desktop_qt_ui/services/async_service.py` — 協程丟後台事件迴圈（`submit_task:18`）；`desktop_qt_ui/services/i18n_service.py` — 多語系（`translate:344` fallback zh_CN；frozen 時 locales 路徑硬編 :27-37）
- **依賴**：manga_translator 後端（translators/ocr dispatch、rendering.text_render、utils.path_manager）
- **坑**：主執行緒外不可直接動 widget（CLAUDE.md:19）；Windows 前台激活需 QTimer.singleShot 否則 RPC_E_CANTCALLOUT（main.py:360）；AsyncJobManager Windows 需手動 WSAStartup（editor/core/async_job_manager.py:37-50）

## 行動

- 回答此模組問題前，回讀上列關鍵檔取證
