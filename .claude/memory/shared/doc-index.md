# doc-index

- Scope: shared
- Confidence: [觀]
- Trigger: 檔案在哪, 哪個檔, where is, doc index, 文件索引
- Tags: L2

## 知識

| 路徑 | 一句話職責 |
|---|---|
| `CLAUDE.md` | 專案導讀：風險分級表 + 技術約束 + 入口對照 |
| `_AIDocs/Project_File_Tree.md` | 完整資料夾佈局與模組職責 |
| `_AIDocs/_CHANGELOG.md` | AI 文件變更歷史 |
| `doc/DEVELOPMENT.md` | 上游開發者文檔（CI/打包注意事項 :298-315） |
| `manga_translator/__main__.py` | CLI/Server 入口（mode 分派） |
| `manga_translator/manga_translator.py` | pipeline 主類（translate_batch :3278） |
| `manga_translator/config.py` | Pydantic 設定模型 + 全部後端 Enum |
| `manga_translator/translators/__init__.py` | 翻譯器策略字典與 dispatch |
| `desktop_qt_ui/main.py` | GUI 入口 + PyInstaller DLL 修復段 |
| `desktop_qt_ui/services/__init__.py` | ServiceContainer 依賴注入中樞 |
| `desktop_qt_ui/app_logic.py` | UI↔後端主呼叫界面（translate_batch 呼叫點 :3663） |
| `packaging/build_packages.py` | PyInstaller 打包入口 |
| `packaging/launch.py` | 安裝/更新邏輯核心（bat/sh 只是外殼） |
| `packaging/VERSION` | 版本檔（現 v2.2.7） |
| `requirements_cpu.txt` | CPU 依賴鎖檔（gpu/_amd/_metal 各有分歧） |

## 行動

- 「XX 在哪個檔」類問題直接查表 → 回讀該檔確認後作答
