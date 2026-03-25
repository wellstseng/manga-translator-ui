# Installation Guide

This document provides detailed installation steps, system requirements, first-run guidance, and troubleshooting notes.

---

## 📋 Table of Contents

- [System Requirements](#system-requirements)
- [Method 1: Install Script](#method-1-install-script)
- [Method 2: Packaged Release](#method-2-packaged-release)
- [Method 3: Run from Source](#method-3-run-from-source)
- [Method 4: Docker Deployment](#method-4-docker-deployment)
- [Method 5: Native macOS Run Apple Silicon](#method-5-native-macos-run-apple-silicon)
- [First Run](#first-run)
- [Troubleshooting](#troubleshooting)
- [Next Steps](#next-steps)

---

## System Requirements

### Minimum

- **Operating system**: Windows 10/11 (64-bit), Linux, or macOS 12+ (Apple Silicon recommended)
- **Memory**: 8 GB RAM
- **Storage**: 5 GB free space for the program and model files
- **Python version** for source runs: Python 3.12

### Recommended

- **Memory**: 16 GB RAM or more
- **GPU**:
  - **NVIDIA GPU**: CUDA 12.x compatible, driver `>= 525.60.13`
    - Recommended VRAM: 6 GB or more
    - Typical supported class: GTX 1060 and above
  - **AMD GPU**: ROCm support is experimental
    - Supported cards: **RX 7000 / 9000 only**
    - ⚠️ RX 5000 / 6000 should use the CPU build
    - ⚠️ AMD GPU is supported through the install-script path, not the packaged release
    - ⚠️ ROCm support on Windows is limited. Linux usually works better
- **Storage**: SSD with 10 GB or more free space

---

## Method 1: Install Script

This is the recommended path for Windows users. It handles environment setup automatically and supports later updates.

> ⚠️ **Network note**: the installer downloads code from GitHub. If your network is unstable, use a proxy or a faster mirror.
>
> 💡 **No Python pre-install required**: the script can install Miniconda automatically.

### Prerequisites

- **No Python pre-install needed**
- **Git is optional**: the script can download a portable Git build for you

### Detailed Steps

#### 1. Get the install script

- Visit the repository: [https://github.com/hgmzhn/manga-translator-ui](https://github.com/hgmzhn/manga-translator-ui)
- Download [`步骤1-首次安装.bat`](https://github.com/hgmzhn/manga-translator-ui/raw/main/步骤1-首次安装.bat)
- Save it into the folder where you want the app installed, for example `D:\manga-translator-ui\`

#### 2. Run the install script

Double-click `步骤1-首次安装.bat`.

The script will:

**2.1 Detect and install Miniconda**

- ✓ If Python or Conda already exists, it uses what is available
- ✗ If not installed:
  - It offers a download source such as the Tsinghua mirror or the official Anaconda source
  - Downloads a Miniconda installer, about 50 MB
  - Silently installs to `<project_dir>\Miniconda3`
  - Configures environment variables automatically
  - **Important**: after the first Miniconda install, you may need to run the script again so the refreshed environment is picked up

**2.2 Detect and install Git**

- ✓ If Git already exists, it uses the system Git
- ✗ If Git is missing, it offers:
  - **Option 1**: download portable Git automatically, recommended
  - **Option 2**: install Git manually and run the script again

**2.3 Choose a download source**

- **Option 1**: official GitHub source
- **Option 2**: mirror source, usually faster in some regions

**2.4 Clone or update the repository**

- First install: clone the repository
- Existing install: update to the latest version automatically

**2.5 Create the Conda environment**

- Creates `conda_env` in the project directory using Python 3.12
- Path: `<project_dir>\conda_env\`
- The environment stays inside the project folder and does not consume system Python space

**2.6 Install dependencies**

- Detects hardware automatically:
  - ✓ **NVIDIA GPU**
    - Checks CUDA version
    - CUDA 12 or newer: installs `requirements_gpu.txt`
    - Older CUDA: prompts you to update the driver or use the CPU build
  - ✓ **AMD GPU**
    - Detects the GPU model and gfx version
    - After confirmation, installs `requirements_amd.txt`
    - **RX 7000 / 9000 only**
    - RX 5000 / 6000 automatically falls back to CPU
  - ✗ **Other GPU / integrated graphics**
    - Installs `requirements_cpu.txt`
- Uses `launch.py` to install the required packages

**2.7 Finish installation**

- Shows the install location
- Optionally launches the app immediately

### Miniconda Layout

**Advantages**

- ✅ Small initial installer, about 50 MB
- ✅ Supports multiple Python versions
- ✅ Keeps environments isolated
- ✅ Includes pip support
- ✅ Installs entirely inside the project directory

**Typical folder layout**

```text
D:\manga-translator-ui\
├── 步骤1-首次安装.bat
├── 步骤2-启动Qt界面.bat
├── 步骤3-检查更新并启动.bat
├── 步骤4-更新维护.bat
├── Miniconda3\
├── conda_env\
├── PortableGit\
├── desktop_qt_ui\
├── manga_translator\
└── ...
```

#### 3. Start the program

After installation, your normal start entry is:

- Double-click `步骤2-启动Qt界面.bat`

You can also use:

- `步骤3-检查更新并启动.bat` to check for updates before launch

#### 4. Update later

When you want the latest version:

- Double-click `步骤4-更新维护.bat`
- Choose the full update option

---

## Method 2: Packaged Release

This is the simplest path if you do not want to install Python, but the download is large.

### 1. Open the release page

Go to [GitHub Releases](https://github.com/hgmzhn/manga-translator-ui/releases).

### 2. Choose a build

**CPU build**

- Filename pattern: `manga-translator-cpu-vX.X.X.zip` or split archives
- Works on all machines
- No dedicated GPU required
- Slower than GPU builds

**GPU build**

- Filename pattern: `manga-translator-gpu-vX.X.X.zip` or split archives
- For NVIDIA GPUs
- Requires CUDA 12.x support
- Faster, but needs compatible hardware

### 3. Split archive notes

If the release is split into multiple archive parts such as `part1.rar`, `part2.rar`, `part3.rar`:

1. Download **all** parts into the same folder
2. Extract only the first part
3. Keep the original filenames unchanged
4. Missing any part will cause extraction to fail

### 4. Install steps

1. **Extract the archive**

   ```text
   Extract to any folder, for example:
   D:\manga-translator\
   ```

2. **Check the structure**

   ```text
   manga-translator/
   ├── app.exe
   ├── _internal/
   ├── fonts/
   ├── models/
   └── examples/
   ```

3. **Run the program**

- Double-click `app.exe`
- The first run will load model files automatically

---

## Method 3: Run from Source

Best for developers or users who want full control.

### 1. Clone the repository

```bash
git clone https://github.com/hgmzhn/manga-translator-ui.git
cd manga-translator-ui
```

### 2. Install dependencies

```bash
# CPU
pip install -r requirements_cpu.txt

# NVIDIA GPU
pip install -r requirements_gpu.txt

# AMD GPU (experimental)
pip install -r requirements_amd.txt

# Apple Silicon / Metal
pip install -r requirements_metal.txt
```

### 3. Run the program

```bash
# Qt desktop UI
python -m desktop_qt_ui.main

# Web UI / API server
python -m manga_translator web
```

---

## Method 4: Docker Deployment

Good for Docker users, server deployments, or users working through panel tools such as BT Panel or Portainer.

### Quick start

**Windows CMD / PowerShell**

```cmd
docker run -d --name manga-translator -p 8000:8000 hgmzhn/manga-translator:latest-cpu
```

**Linux / macOS**

```bash
docker run -d --name manga-translator -p 8000:8000 hgmzhn/manga-translator:latest-cpu
```

After startup:

- 🌐 User UI: `http://localhost:8000`
- 🔧 Admin UI: `http://localhost:8000/admin`

### Image registries

This project publishes the same image to two registries:

**Docker Hub**

- CPU: `hgmzhn/manga-translator:latest-cpu`
- GPU: `hgmzhn/manga-translator:latest-gpu`

**GitHub Container Registry**

- CPU: `ghcr.io/hgmzhn/manga-translator:latest-cpu`
- GPU: `ghcr.io/hgmzhn/manga-translator:latest-gpu`

### Port mapping

- **Container port**: `8000`
- **Host port**: `8000` by default, can be changed

### Environment variables

> 💡 All environment variables are optional. Reasonable defaults are used when possible.

#### Basic settings

| Variable | Example | Default | Description |
|--------|--------|--------|------|
| `MT_WEB_HOST` | `0.0.0.0` | `0.0.0.0` | Listen address |
| `MT_WEB_PORT` | `8000` | `8000` | Web server port |
| `MT_USE_GPU` | `true` | `false` | Enable GPU, only meaningful for GPU images |
| `MT_MODELS_TTL` | `300` | `0` | Model lifetime in memory, in seconds. `0` keeps models loaded |
| `MT_RETRY_ATTEMPTS` | `-1` | `None` | Retry count for failures. `-1` means unlimited |
| `MT_VERBOSE` | `true` | `false` | Enable verbose logs |
| `MANGA_TRANSLATOR_ADMIN_PASSWORD` | `your_password` | none | Admin password, at least 6 characters |

#### API keys

**OpenAI family**

| Variable | Description |
|--------|------|
| `OPENAI_API_KEY` | OpenAI API key, used by OpenAI translators |
| `OPENAI_MODEL` | OpenAI model name |
| `OPENAI_API_BASE` | OpenAI-compatible base URL |
| `OPENAI_HTTP_PROXY` | Optional HTTP proxy |
| `OPENAI_GLOSSARY_PATH` | Optional glossary path |

**Gemini family**

| Variable | Description |
|--------|------|
| `GEMINI_API_KEY` | Gemini API key |
| `GEMINI_MODEL` | Gemini model name |
| `GEMINI_API_BASE` | Gemini API base URL |

**Other commercial providers**

| Variable | Description |
|--------|------|
| `DEEPL_AUTH_KEY` | DeepL API key |
| `GROQ_API_KEY` | Groq API key |
| `GROQ_MODEL` | Groq model name |
| `DEEPSEEK_API_KEY` | DeepSeek API key |
| `DEEPSEEK_API_BASE` | DeepSeek API base URL |
| `DEEPSEEK_MODEL` | DeepSeek model name |

**Domestic services**

| Variable | Description |
|--------|------|
| `BAIDU_APP_ID` | Baidu Translate App ID |
| `BAIDU_SECRET_KEY` | Baidu Translate secret |
| `YOUDAO_APP_KEY` | Youdao app key |
| `YOUDAO_SECRET_KEY` | Youdao secret |
| `CAIYUN_TOKEN` | Caiyun API token |

**Local / custom models**

| Variable | Description |
|--------|------|
| `SAKURA_API_BASE` | Sakura API base URL |
| `SAKURA_DICT_PATH` | Sakura glossary path |
| `CUSTOM_OPENAI_API_KEY` | Custom OpenAI-compatible API key |
| `CUSTOM_OPENAI_API_BASE` | Custom OpenAI-compatible base URL |
| `CUSTOM_OPENAI_MODEL` | Custom model name |
| `CUSTOM_OPENAI_MODEL_CONF` | Custom model config |

### Access URLs

After deployment:

- **User UI**: `http://server-ip:8000`
- **Admin UI**: `http://server-ip:8000/admin`

### BT Panel deployment outline

1. Open port `8000`
2. Install Docker manager from the panel
3. Pull the image
4. Create a container with `8000:8000`
5. Add environment variables if needed
6. Start the container and open the site

> ⚠️ Docker support is still experimental.

---

## Method 5: Native macOS Run Apple Silicon

Designed for Apple Silicon Macs and uses MPS acceleration when available.

### System requirements

- **Hardware**: Mac with Apple Silicon preferred. Intel Mac can still run in CPU mode
- **OS**: macOS 12.0 or later
- **Tools**: Xcode Command Line Tools, the script checks and prompts if needed

### Script mapping

| Script | Purpose | Windows equivalent |
|---------|------|-------------|
| `macOS_1_首次安装.sh` | First-time install, clone, Miniforge install, dependency install | `步骤1-首次安装.bat` |
| `macOS_2_启动Qt界面.sh` | Start the Qt UI | `步骤2-启动Qt界面.bat` |
| `macOS_3_检查更新并启动.sh` | Update check then launch | `步骤3-检查更新并启动.bat` |
| `macOS_4_更新维护.sh` | Maintenance menu | `步骤4-更新维护.bat` |

### Install steps

**Option 1: Quick install**

```bash
# 1. Download script
curl -O https://raw.githubusercontent.com/hgmzhn/manga-translator-ui/main/macOS_1_首次安装.sh

# 2. Make it executable
chmod +x macOS_1_首次安装.sh

# 3. Run installer
./macOS_1_首次安装.sh
```

The script automatically:

- Checks Xcode Command Line Tools
- Clones the project
- Installs Miniforge if needed
- Creates the `manga-env` environment with Python 3.12
- Installs `requirements_metal.txt`
- Configures MPS acceleration

**Option 2: Clone manually first**

```bash
git clone https://github.com/hgmzhn/manga-translator-ui.git
cd manga-translator-ui
chmod +x macOS_*.sh
./macOS_1_首次安装.sh
```

### Verify and run

```bash
# Normal launch
./macOS_2_启动Qt界面.sh

# Update check and launch
./macOS_3_检查更新并启动.sh

# Maintenance menu
./macOS_4_更新维护.sh
```

### FAQ

**Q: How long does the first install take?**
About 10 to 20 minutes depending on your network.

**Q: Can Intel Mac run it?**
Yes, but it will use CPU mode.

**Q: How do I update later?**
Run `./macOS_4_更新维护.sh` and choose the full update option.

---

## First Run

This section uses the current Qt UI labels from `en_US.json`.

### 1. Launch the program

Start one of these:

- `步骤2-启动Qt界面.bat`
- `app.exe`
- `python -m desktop_qt_ui.main`

On the first run, the app will:

- Load AI models, which can take several minutes
- Initialize translation backends
- Open the main window on `Translation Interface`

### 2. CPU build users: turn off GPU

If you are using the CPU package or a machine without a compatible GPU:

1. Open `Settings`
2. Open the `General` section
3. Turn off `Use GPU`

> ⚠️ Enabling `Use GPU` on a CPU-only setup can cause crashes or startup failures.

### 3. Set the output directory

1. Stay on `Translation Interface`
2. Find `Output Directory:`
3. Click `Browse...`
4. Choose where translated results should be saved

### 4. Configure your translator

If you want online translation:

1. Open `API Management`
2. Fill the required key such as `OpenAI API Key` or `Gemini API Key`
3. Return to `Translation Interface`
4. Choose `Translator`
5. Choose `Target Language`

Recommended first choices:

- `OpenAI High Quality`
- `Gemini High Quality`

### 5. Add images

You can add input pages in three ways:

- Click `Add Files`
- Click `Add Folder`
- Drag and drop files or folders into the file list

Supported formats include `.jpg`, `.jpeg`, `.png`, `.webp`, and `.bmp`.

### 6. Start translation

1. Confirm the settings
2. Click `Start Translation`
3. Wait for the task to finish
4. The output is saved to the selected output folder

If you want to fine-tune the result later, open it in `Editor View`.

---

## Troubleshooting

### The program does not start

**Symptoms**

- `app.exe` does nothing
- The window flashes and closes immediately

**Try this**

1. Make sure the package is fully extracted
2. Check whether antivirus blocked the executable
3. Run the launcher as administrator
4. Check the runtime log under `result/log_*.txt`

### Missing DLL files

**Symptoms**

- Error messages about `VCRUNTIME140.dll` or similar DLLs

**Try this**

1. Install [Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)
2. Reboot the system
3. Start the app again

### GPU build crashes

**Symptoms**

- Crash or initialization error in GPU mode

**Try this**

1. Confirm the GPU supports CUDA 12.x
2. Update the NVIDIA driver
3. If the issue is ONNX-specific, open `Settings` -> `General` and enable `Disable ONNX GPU Acceleration`
4. If the machine is not compatible, switch to the CPU build

### Translation fails after adding images

**Try this**

1. Confirm the image format is supported
2. Check whether model files are complete
3. Turn on `Verbose Logging`
4. Review:
   - `result/log_*.txt`
   - `result/<timestamp-image-target-translator>/`

### Model loading is very slow

**Why this happens**

- The first run needs to load several AI models and supporting files

**Suggestions**

- Wait 5 to 10 minutes on the first launch
- Later runs are much faster because models are cached
- Install on an SSD if possible

---

## Next Steps

After installation, these documents are the most useful next reads:

- [Features](./FEATURES.md)
- [Workflows](./WORKFLOWS.md)
- [Settings Reference](./SETTINGS.md)

---

Back to [README_EN](../../README_EN.md)
