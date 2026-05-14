# manga-translator-ui — AI 分析文件索引

> 本資料夾包含由 AI 輔助產出的專案分析文件。
> 最近更新：2026-05-12

---

## 文件清單

| # | 文件名稱 | 說明 |
|---|---------|------|
| 1 | Project_File_Tree.md | 專案資料夾結構摘要 |

---

## 架構一句話摘要

漫畫翻譯桌面應用：`manga_translator/` 後端 pipeline（檢測 → OCR → 翻譯 → 修復 → 嵌字） + `desktop_qt_ui/` PyQt6 前端（服務容器架構，可視化編輯器），打包用 PyInstaller，支援 CPU / NVIDIA GPU / AMD / Apple Metal 多平台。

---

## 追蹤用途速查

| 想找什麼 | 看哪裡 |
|---------|--------|
| 整體資料夾佈局、模組職責 | Project_File_Tree.md |
| 變更歷史 | _CHANGELOG.md |
| 上游官方 CHANGELOG（v1.7+） | `doc/CHANGELOG_v*.md` |
| 安裝/使用/CLI/API 設定 | `doc/INSTALLATION.md` etc. |
| 上游官方專案結構說明 | `doc/DEVELOPMENT.md` |
