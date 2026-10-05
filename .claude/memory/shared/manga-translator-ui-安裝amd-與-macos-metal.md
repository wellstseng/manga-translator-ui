# manga-translator-ui 安裝：AMD 與 macOS Metal

- Scope: shared
- Author: catclaw-ext-merge
- Confidence: [臨]
- Trigger: requirements_amd.txt, ROCm Linux, AMD 安裝, macOS_1_首次安装.sh, requirements_metal.txt, MPS 支援, Metal 安裝
- Created-at: 2026-07-02

## 知識

- AMD 用戶需手動安裝 `requirements_amd.txt`，專案沒有專屬的一鍵安裝腳本；ROCm 支援僅限 Linux 平台（2026-07）。
- macOS（Metal）用戶用專屬腳本 `macOS_1_首次安装.sh` 安裝；該腳本會安裝 `requirements_metal.txt` 並驗證 MPS 支援（2026-07）。

## 行動

- （依知識內容判斷）
