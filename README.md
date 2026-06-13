# mcu-env

面向 STM32 / GD32 裸机开发的便携式 MCU 工具链环境，提供类似 ESP-IDF `idf.py` 的命令行体验。

本仓库包含：

- 自包含的交叉编译与构建工具（可选，见下方「工具目录」）
- Python CLI：`mcuenv.py`
- 跨平台环境激活脚本：`export.ps1` / `export.sh`
- CMake ARM 工具链文件与 OpenOCD 烧录封装

## 功能概览

| 命令 | 说明 |
|------|------|
| `doctor` | 检查 Python、工具路径与各二进制是否可用 |
| `env-info` | 显示解析后的环境路径 |
| `export` | 输出 shell 激活语句（PowerShell / Bash） |
| `list-targets` | 列出支持的 STM32 / GD32 目标预设 |
| `set-target` | 为当前工程写入 `mcuenv.project.toml` |
| `build` | CMake + Ninja 配置并编译 |
| `clean` | 清理工程 build 目录 |
| `flash` | 通过 OpenOCD 烧录 ELF |

## 环境要求

- **Python 3.11+**（使用标准库 `tomllib`，无第三方依赖）
- **Windows** 或 **Linux**（macOS 理论上可用，需自行验证工具包）

## 目录结构

```text
mcu-env/
├── mcuenv.py                 # CLI 入口
├── mcuenv.toml               # 全局配置（工具路径等）
├── export.ps1                # Windows 环境激活
├── export.sh                 # Linux/macOS 环境激活
├── cmake/
│   └── toolchain-arm-none-eabi.cmake
├── mcuenv/                   # Python 包
└── tools/                    # 预置工具（体积大，默认不提交 Git）
    ├── arm-gnu-toolchain/
    ├── cmake/
    ├── ninja/
    └── openocd/
```

## 工具目录

`tools/` 下为预解压的交叉编译链与辅助工具，体积较大，**默认已在 `.gitignore` 中排除**。

克隆仓库后，请在本机按 `mcuenv.toml` 中的相对路径放置工具，例如：

```text
tools/arm-gnu-toolchain/bin/arm-none-eabi-gcc
tools/cmake/bin/cmake
tools/ninja/bin/ninja
tools/openocd/bin/openocd
tools/openocd/openocd/scripts/   # OpenOCD 脚本目录
```

路径可在 `mcuenv.toml` 的 `[paths]` 段修改。

运行自检确认环境就绪：

```bash
python mcuenv.py doctor
```

## 快速开始

### 1. 激活环境（可选）

激活后，当前终端可直接使用 `arm-none-eabi-gcc`、`cmake`、`openocd` 等命令。

**Windows PowerShell：**

```powershell
. D:\path\to\mcu-env\export.ps1
```

**Linux / macOS：**

```bash
source /path/to/mcu-env/export.sh
```

也可以不激活，直接通过 `mcuenv.py` 调用（脚本会在子进程中注入 PATH）。

### 2. 检查环境

```bash
python mcuenv.py doctor
python mcuenv.py env-info
python mcuenv.py list-targets
```

### 3. 在裸机工程中构建与烧录

在包含 `CMakeLists.txt` 的工程目录中：

```bash
python /path/to/mcuenv.py set-target stm32f103c8
python /path/to/mcuenv.py build
python /path/to/mcuenv.py flash
```

会在工程根目录生成 `mcuenv.project.toml`，例如：

```toml
[project]
name = "my-firmware"
target = "stm32f103c8"

[build]
build_dir = "build"

[flash]
interface = "stlink"
openocd_target = "stm32f1x"
```

默认烧录 `build/<项目名>.elf`。若 CMake 输出文件名不同，可在 `[build]` 中设置 `elf_name`。

## 支持的目标预设

| 预设名 | 系列 | MCU | OpenOCD Target |
|--------|------|-----|----------------|
| `stm32f103c8` | STM32 | STM32F103C8 | `stm32f1x` |
| `stm32f303cb` | STM32 | STM32F303CB | `stm32f3x` |
| `stm32f407vg` | STM32 | STM32F407VG | `stm32f4x` |
| `stm32g431cb` | STM32 | STM32G431CB | `stm32g4x` |
| `stm32h743zi` | STM32 | STM32H743ZI | `stm32h7x` |
| `gd32f103c8` | GD32 | GD32F103C8 | `stm32f1x` |
| `gd32f303cc` | GD32 | GD32F303CC | `stm32f2x` |
| `gd32f450ik` | GD32 | GD32F450IK | `stm32f4x` |
| `gd32e230c8` | GD32 | GD32E230C8 | `gd32e23x` |

GD32 的 ARM 系列多数映射到 STM32 兼容的 OpenOCD target；若某块板子调试异常，可在 `mcuenv.project.toml` 的 `[flash]` 段手动覆盖 `openocd_target` / `interface`。

筛选某一系列：

```bash
python mcuenv.py list-targets --family stm32
python mcuenv.py list-targets --family gd32
```

## 配置说明

### 全局配置 `mcuenv.toml`

定义工具路径、默认构建生成器、OpenOCD 默认接口等。路径相对于 `MCUENV_ROOT`（即本仓库根目录）。

### 工程配置 `mcuenv.project.toml`

每个 firmware 工程一份，由 `set-target` 生成或手动编辑。工程根目录需存在该文件或 `CMakeLists.txt`，`mcuenv.py` 才能定位项目。

## 环境变量

激活环境后会设置：

| 变量 | 说明 |
|------|------|
| `MCUENV_ROOT` | 本环境根目录 |
| `PATH` | 追加 toolchain / cmake / ninja / openocd |
| `OPENOCD_SCRIPTS` | OpenOCD 脚本目录 |
| `CMAKE_TOOLCHAIN_FILE` | ARM 交叉编译 toolchain 文件 |
| `CROSS_COMPILE` | `arm-none-eabi-` |
| `CC` / `CXX` | 交叉编译器 |

## 推送到远程仓库

```bash
git init
git add README.md mcuenv.py mcuenv.toml export.ps1 export.sh cmake/ mcuenv/ .gitignore
git commit -m "Add portable MCU development environment tooling"
git remote add origin <your-remote-url>
git push -u origin main
```

`tools/` 默认不纳入版本控制。若团队需要共享二进制，可考虑：

- Git LFS
- Release 附件分发
- 内部制品库 / 下载脚本

## 路线图

- [ ] 最小 blink 裸机工程模板
- [ ] CMSIS + RTOS 工程模板
- [ ] MCP Server（供 Cursor / Agent 调用 build / flash / doctor）
- [ ] `mcuenv new` 工程脚手架

## 许可证

- `mcuenv/` 及相关脚本：随本仓库约定使用
- `tools/` 内第三方工具（GCC、CMake、Ninja、OpenOCD 等）遵循各自上游许可证
