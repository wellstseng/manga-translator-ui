# pitfall-pyinstaller-dll-order

- Scope: shared
- Confidence: [觀]
- Trigger: PyInstaller, onnxruntime, DLL, c10.dll, PyQt6, torch import 順序, _MEIPASS, add_dll_directory
- Tags: pitfall

## 知識

- **症狀**：PyInstaller 打包版啟動時 onnxruntime 或 torch（c10.dll）載入失敗；或 PyQt6 與 torch 同時使用時 DLL 衝突崩潰
- **根因**：(a) PyInstaller 環境 DLL 搜尋路徑不含 `_MEIPASS/onnxruntime/capi`；(b) PyQt6 先 import 會把 Qt 的 DLL 路徑插到前面，干擾 c10.dll 載入（pytorch issue 166628）
- **解法**：(a) frozen 時 `os.add_dll_directory` 補 `_MEIPASS` 與 `onnxruntime/capi`（`desktop_qt_ui/main.py:24-33`；runtime hook `packaging/pyi_rth_onnxruntime.py:5-10`）；(b) **一律在 import PyQt6 之前先 import torch**（`desktop_qt_ui/main.py:35-40`、`manga_translator/__main__.py:17-19` 兩處入口都這樣做）
- **適用條件**：Windows + PyInstaller 打包環境為主；torch+PyQt6 共存的任何入口檔都要遵守 import 順序
- **來源**：manga-translator-ui / 2026-07-02 / onboard 實讀 desktop_qt_ui/main.py:24-40

## 行動

- 觸發同技術關鍵詞時主動提示此坑；新增入口檔時檢查 import 順序
