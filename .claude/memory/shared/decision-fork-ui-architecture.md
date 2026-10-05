# decision-fork-ui-architecture

- Scope: shared
- Confidence: [觀]
- Trigger: fork, 上游, upstream, 為什麼, why, 設計決策, 服務容器, DI
- Tags: decision

## 知識

- **決策 1（fork 定位）**：fork 自 zyddnys/manga-image-translator，本 fork 只加值不改本體——新增 PyQt6 桌面 UI、可視化編輯器、多平台打包/啟動腳本；上游 pipeline 保持可同步
  - 出處：`_AIDocs/Project_File_Tree.md:120`、`CLAUDE.md:3`；GPL-3.0 約束（`CLAUDE.md:24`）
- **決策 2（UI 架構）**：前端採服務容器（依賴注入）——`desktop_qt_ui/services/__init__.py` 的 ServiceContainer 為中樞，新服務必須在此註冊（`CLAUDE.md:22`）；async 統一走 `desktop_qt_ui/services/async_service.py`，主執行緒外不動 widget（`CLAUDE.md:19`）
- **決策 3（多平台策略）**：PyInstaller 打包只覆蓋 cpu/gpu（`packaging/build_packages.py:152` choices 限定）；metal/amd 走 conda 原始碼安裝——理由未記載，現況推斷為 mac/AMD 使用者少且 ROCm 實驗性（`requirements_amd.txt:24-43` 明言）
- **影響範圍**：改 pipeline 串接屬高風險（CLAUDE.md 風險分級）；requirements 四檔會分歧、改一個要評估同步其他（`CLAUDE.md:20`）

## 行動

- 「為什麼這樣設計」類問題先回讀出處檔，未記載部分明講「未記載，現況推斷」
