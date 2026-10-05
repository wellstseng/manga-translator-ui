# torch 與 PyQt6 匯入順序及打包變體限制

- Scope: shared
- Author: catclaw-ext-merge
- Confidence: [臨]
- Trigger: torch PyQt6 匯入順序, c10.dll, Qt DLL 衝突, desktop_qt_ui/main.py, build_packages.py, cpu gpu 變體 metal amd, onnxruntime DLL 修復
- Created-at: 2026-07-02
- Related: pitfall-pyinstaller-dll-order, module-packaging, module-desktop-qt-ui

## 知識

- 專案的 CLI 與 GUI 進入點都先 import `torch` 再 import `PyQt6`，避免 PyQt6 的 Qt DLL 路徑干擾 PyTorch 載入 `c10.dll` 而造成 DLL 衝突（2026-07-02）。
- `desktop_qt_ui/main.py`（GUI 端）因多了一段「PyInstaller打包 onnxruntime DLL 修復」區塊，與 CLI 端相比有系統性的 -3 行號偏移（2026-07-02）。
- PyInstaller 打包腳本 `build_packages.py` 硬編碼只支援 `cpu` 與 `gpu` 兩種變體，沒有 `metal` 或 `amd` 的建置路徑（2026-07-02）。

## 行動

- （依知識內容判斷）
