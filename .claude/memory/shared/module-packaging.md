# module-packaging

- Scope: shared
- Confidence: [觀]
- Trigger: packaging, PyInstaller, 打包, build, Docker, requirements, 依賴鎖檔, 啟動腳本, launch, 更新, conda, Miniforge
- Tags: L1

## 知識

- **職責**：多平台打包（PyInstaller 只有 cpu/gpu 兩種；metal/amd 走 conda 原始碼安裝）、Docker 部署、安裝/更新邏輯、版本管理
- **關鍵檔**：
  - `packaging/build_packages.py` — 打包入口（CLI `<version> --build {cpu|gpu|both}` :150-156；跑對應 spec :105；版本源 `packaging/VERSION` :56-84）
  - `packaging/launch.py` — 安裝/更新真正邏輯核心 95KB（旗標 `--frozen/--maintenance/--update/--reinstall-torch` :2249-2259；AMD ROCm 兩階段安裝 :888+）。**改安裝/更新行為不要只改 .bat/.sh 外殼**（`doc/DEVELOPMENT.md:305`）
  - `packaging/manga-translator-cpu.spec` / `packaging/manga-translator-gpu.spec` — 入口皆 `desktop_qt_ui/main.py`（各 :50），差異僅 COLLECT name；都 collect_all('onnxruntime') :35
  - `packaging/pyi_rth_onnxruntime.py` — Windows runtime hook（`_MEIPASS/onnxruntime/capi` 加 DLL 搜尋路徑 :5-10）
  - `packaging/Dockerfile` — 多階段 cpu/gpu base（:9/:36），CMD 跑 web server :126-134
  - `macOS_1_首次安装.sh`〜`macOS_4_更新维护.sh` — Miniforge3 + conda env `manga-env`（Python 3.12）；macOS_3 啟動前跑 `packaging/check_version.py`
- **依賴鎖檔差異**：cpu=torch cpu 源 + onnxruntime；gpu=cu128 + onnxruntime-gpu + xformers；metal=MPS 預設源（勿用 CUDA 源）；amd=torch 不在檔內、由 launch.py 裝 ROCm、**numpy 刻意不釘**（`requirements_amd.txt:72`）
- **坑**：packaging 套件須 <25.0（launch.py:897-925 自動降級）；pydensecrf Windows 用預編譯 wheel、mac/linux 源碼編；新增打包資源要同步改 CI workflow 複製 `_internal` 步驟（`doc/DEVELOPMENT.md:315`）

## 行動

- 回答此模組問題前，回讀上列關鍵檔取證；依賴/打包屬高風險層級，動工前見 CLAUDE.md 風險分級
