# mcu-env

面向 STM32 / GD32 裸机开发的便携式 MCU 工具链环境，提供类似 ESP-IDF `idf.py` 的命令行体验。

本仓库包含：

- 自包含的交叉编译与构建工具（可选，见下方「工具目录」）
- Python CLI：`mcuenv.py`
- 跨平台环境激活脚本：`export.ps1` / `export.sh`
- CMake ARM 工具链文件与多 backend 烧录（OpenOCD / pyOCD / J-Link）

## 功能概览

| 命令 | 说明 |
|------|------|
| `doctor` | 检查 Python、工具路径与各二进制是否可用 |
| `env-info` | 显示解析后的环境路径 |
| `export` | 输出 shell 激活语句（PowerShell / Bash） |
| `list-targets` | 列出支持的 STM32 / GD32 目标预设 |
| `set-target` | 为当前工程写入 `mcuenv.project.toml` |
| `build` | CMake + Ninja 配置并编译 |
| `clean` | 删除编译产物（保留 `build/` 内 CMake 缓存） |
| `fullclean` | 删除整个 `build/` 目录（下次 build 重新 configure） |
| `flash` | 按工程配置烧录 ELF（OpenOCD / pyOCD / J-Link） |
| `erase` | 整片擦除 Flash（pyOCD / J-Link） |
| `shell init` | 生成或安装 `mcuenv-on` 到 shell profile |
| `registry init/export/sync-status` | 管理 SQLite registry（芯片 + packages/manuals） |
| `web serve` | 启动 registry Web 管理后台 |

## 环境要求

- **Python 3.11+**（使用标准库 `tomllib`，无第三方依赖）
- **Windows** 或 **Linux**（macOS 理论上可用，需自行验证工具包）

## 目录结构

```text
mcu-env/
├── mcuenv.py                 # CLI 入口（Python 实现）
├── bin/
│   ├── mcuenv.py             # Linux/macOS 启动器（激活后进 PATH）
│   └── mcuenv.py.cmd         # Windows 启动器（激活后进 PATH）
├── mcuenv.toml               # 全局配置（工具路径等）
├── export.ps1                # Windows 环境激活
├── export.sh                 # Linux/macOS 环境激活
├── cmake/
│   ├── toolchain-base-arm.cmake      # ARM 工具名 + 通用 flags 逻辑
│   ├── toolchain-base-riscv.cmake    # RISC-V 工具名（profile 待扩展）
│   ├── toolchain-base.cmake          # 兼容 shim → base-arm
│   ├── toolchain-cortex-m0.cmake
│   ├── toolchain-cortex-m0plus.cmake
│   ├── toolchain-cortex-m3.cmake
│   ├── toolchain-cortex-m4.cmake
│   ├── toolchain-cortex-m7.cmake
│   ├── toolchain-cortex-m33.cmake
│   └── toolchain-arm-none-eabi.cmake   # fallback → M4 profile
├── mcuenv/                   # Python 包
├── registry/                 # SDK / 手册 TOML 快照（进 Git）
│   ├── packages.toml
│   └── manuals.toml
├── data/                     # SQLite registry（默认不进 Git）
│   └── registry.db
├── packages/                 # SDK 库（本地安装，默认不进 Git）
│   ├── stm32/
│   └── gd32/
├── manuals/                  # 芯片手册 PDF（本地存放，默认不进 Git）
│   ├── stm32/
│   └── gd32/
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
tools/pyocd/pyocd               # 或 Scripts/pyocd（pip --target 布局）
```

路径可在 `mcuenv.toml` 的 `[paths]` 段修改；本机差异请写入 **`mcuenv.local.toml`**（已 gitignore，不污染仓库默认值）。

**ARM GNU 工具链（Linux 示例）：** 从 [ARM 官方发布页](https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads) 下载 `arm-gnu-toolchain-*-x86_64-arm-none-eabi.tar.xz`，解压后把 `bin/` 对齐到 `tools/arm-gnu-toolchain/bin/`（解压命令：`tar -Jxvf …tar.xz`，`-J` 表示 xz；若报 `Compressed data is corrupt` 说明下载不完整，需重新下载）。

安装工具后，先激活环境再自检：

```bash
mcuenv-on
mcuenv.py doctor
```

## 快速开始

用法类似 ESP-IDF：先 `mcuenv-on` 进环境，再在工程目录里 `mcuenv.py build`。

### 0. 一次性注册 `mcuenv-on`（推荐）

```powershell
python D:\mcu-env\mcuenv.py shell init --install
```

Linux / macOS：

```bash
python /path/to/mcu-env/mcuenv.py shell init --install --format bash
```

重启终端后，任意目录可用：

```powershell
mcuenv-on      # 激活环境
```

仅预览 profile 片段，不加 `--install`：

```powershell
python D:\mcu-env\mcuenv.py shell init --format ps1
```

### 1. 激活环境

激活后可直接使用：

- `mcuenv.py doctor` / `mcuenv.py build`（类似 `idf.py`）
- `arm-none-eabi-gcc`、`cmake`、`openocd` 等工具

**Windows PowerShell：**

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned   # 首次可能需要
mcuenv-on
# 或: . D:\mcu-env\export.ps1
```

**Linux / macOS：**

```bash
mcuenv-on
# 或: source /path/to/mcu-env/export.sh
```

激活成功后会看到：

```text
mcuenv activated: /path/to/mcu-env
Run 'mcuenv.py doctor' to verify the environment.
Run 'deactivate' when you want to leave this environment.
(mcuenv) user@host:~/your/project$    # Linux Bash（绿色前缀）
(mcuenv) PS D:\your\project>          # Windows PowerShell
```

`build` / `clean` / `fullclean` / `flash` / `erase` / `doctor` **必须先 `mcuenv-on`**，子进程继承当前终端 PATH，不会自行注入环境。

**Linux / Debian 说明：**

- Bash 提示符前缀由 `export.sh` 注入 `PS1`；颜色转义使用 Bash 可识别的 `\e`（勿在 `PS1` 中写 `\x1b` 字面量）。
- `export.sh` 仅在激活过程中启用严格模式（`set -euo pipefail`），结束后会恢复你原来的 shell 选项，因此 `mcuenv.py doctor` 出现 `[FAIL]` 时**不会**关闭终端。
- `bin/mcuenv.py` 在 Linux 上需有可执行权限；仓库内已设置 `+x`，克隆后可直接进 PATH 使用。
- 本机路径与工具布局可在 `mcuenv.local.toml` 中覆盖（见下方配置说明），无需改仓库里的 `mcuenv.toml`。

`build`、`clean`、`fullclean`、`flash`、`erase` 完成后会打印耗时。`flash` / `erase`（J-Link）在 DLL 回调可用时显示进度条；`build` 默认输出 Ninja 的 `[n/m]` 步骤行（含 POST_BUILD 的 `size` 等）。

**详细编译日志**（Keil 风格，仅显示 `compiling xxx.c`，不刷屏 gcc 命令行）：

```bash
mcuenv.py --verbose build
```

> **PowerShell**：请写 `--verbose`，不要写 `-v`。激活后的 `mcuenv.py` 函数会把 `-v` 当成 PowerShell 的 `-Verbose`，传不到 Python。也可用 `mcuenv.py --% -v build`。

### 2. 初始化芯片 registry

```bash
mcuenv.py registry init
mcuenv.py list-targets
```

芯片目录保存在 `data/registry.db`（可用 `mcuenv.py web serve` 编辑）。首次 `registry init` 会写入 4 颗内置芯片。

### 3. 检查环境

```bash
mcuenv.py doctor
mcuenv.py env-info
```

### 4. 在裸机工程中构建与烧录

在包含 `CMakeLists.txt` 的工程目录中：

```bash
mcuenv.py set-target stm32f103c8t6
mcuenv.py build
mcuenv.py flash
mcuenv.py fullclean   # 改 CMakeLists / toolchain 后仍不生效时用
mcuenv.py erase    # 需 [flash].tool 为 pyocd 或 jlink
```

会在工程根目录生成 `mcuenv.project.toml`，例如：

```toml
[project]
name = "my-firmware"
target = "stm32f103c8t6"

[build]
# CMake 构建输出目录
build_dir = "build"
# 工程 toolchain（相对工程根）；留空则按 chip cpu 或 mcuenv.toml fallback
toolchain_file = ""
# 链接脚本（相对工程根）；留空则不注入，由 CMakeLists 指定
linker_script = ""
# 编译前脚本（相对工程根）；空列表表示不执行
pre_build = []
# 编译后脚本；空列表表示不执行
post_build = []

[flash]
# 烧录软件栈：openocd | pyocd | jlink
tool = "openocd"
# 物理调试探针：stlink | jlink | cmsis-dap
probe = "stlink"
# 烧录完成后：reset_and_run | reset_halt | none
after_program = "reset_and_run"
# 烧录固件（相对工程根，支持 glob）；留空则使用 build_dir/<项目名>.elf
image = "build/my-firmware.elf"

[flash.jlink]
device = "STM32F103C8"
interface = "swd"
speed_khz = 4000
serial = ""
reset_strategy = ""
script = ""

[flash.openocd]
adapter = "stlink"
target = "stm32f1x"
transport = "swd"
adapter_speed_khz = 0
extra_commands = ""

[flash.pyocd]
target = "stm32f103c8"
probe_uid = ""
frequency_hz = 4000000
connect_mode = "halt"
pack = ""

[debug]
probe = "stlink"
backend = "openocd"
on_connect = "reset_halt"
gdb_port = 3333
jlink_device = "STM32F103C8"
pyocd_target = "stm32f103c8"
```

默认烧录 `[flash].image` 所指文件；`set-target` 会写入 `build/<项目名>.elf`。`image` 留空时按 `build_dir` 与 `[project].name` 推导。linker 脚本内容手改文件，TOML 只写路径。

## 内置芯片（SQLite）

| id | 系列 | MCU | CPU | 默认 tool |
|----|------|-----|-----|-----------|
| `stm32f103c8t6` | STM32 | STM32F103C8T6 | cortex-m3 | openocd |
| `stm32h750xbh6` | STM32 | STM32H750XBH6 | cortex-m7 | openocd |
| `gd32f303vet6` | GD32 | GD32F303VET6 | cortex-m4 | pyocd |
| `gd32f527zmt7` | GD32 | GD32F527ZMT7 | cortex-m33 | jlink |

`[flash].tool` 可选 `openocd`、`pyocd`、`jlink`；`probe` 为 `stlink` / `jlink` / `cmsis-dap`。各 backend 参数分别在 `[flash.jlink]`、`[flash.openocd]`、`[flash.pyocd]`。pyOCD 默认使用 `mcuenv.toml` 中 `[paths].pyocd`（激活后进 PATH），也可系统 `pip install pyocd`。

**J-Link**：烧录/擦除通过 SEGGER DLL（ctypes）：64 位 Python 加载 `JLink_x64.dll`，32 位加载 `JLinkARM.dll`。查找顺序：`[paths].jlink` → 注册表 `InstallPath`。进度条来自 `JLINK_SetFlashProgProgressCallback`。片上 Flash 由 SEGGER 设备库中的 **RAM FlashLoader** 执行擦写。仍保留 Commander（`JLinkExe`）路径解析（`doctor` 等），但 `flash` / `erase` 不再调用 `JLink.exe` 脚本。

**擦除**：`mcuenv.py erase` 支持 `pyocd`（`pyocd erase --chip`）与 `jlink`（`JLINK_EraseChip`，整片擦除，通常为数秒级）；OpenOCD 暂未适配。

**`[debug]`**：`set-target` 会写入调试相关字段，供 IDE / 后续 `mcuenv debug` 使用；**当前 CLI 尚未读取该段**，烧录请配置 `[flash]`。

筛选某一系列：

```bash
mcuenv.py list-targets --family stm32
mcuenv.py list-targets --family gd32
```

## Registry Web 管理（SQLite）

芯片目录仅保存在 `data/registry.db`；`registry/packages.toml` 与 `registry/manuals.toml` 仍可作为 SDK/手册的 Git 快照。

### 安装 Web 依赖

```bash
python -m pip install -r requirements-web.txt
```

### 初始化数据库

```bash
python D:\mcu-env\mcuenv.py registry init
```

会写入 4 颗内置芯片，并导入 `packages.toml` / `manuals.toml`（若存在）。

### 启动管理后台

```bash
python D:\mcu-env\mcuenv.py web serve
```

浏览器打开 [http://127.0.0.1:7654](http://127.0.0.1:7654)，可管理：

- 芯片（chips，SQLite 唯一源）
- SDK 包（packages）
- 手册（manuals）

常用操作：

- **扫描文件状态**：根据 `packages/`、`manuals/` 实际文件更新 `installed/missing`
- **导出 TOML**：把 packages/manuals 写回 `registry/*.toml`
- **从 TOML 重新导入**：仅重新导入 packages/manuals

数据库默认路径：`data/registry.db`（可在 `mcuenv.toml` 的 `[registry]` 段修改）。

## 环境模型

```text
mcuenv.toml          工具目录、registry 路径、默认 flash/build 选项
    ↓ mcuenv-on
终端 PATH            bin/、toolchain、cmake、ninja、openocd、pyocd
    + OPENOCD_SCRIPTS / MCUENV_ROOT / MCUENV_ACTIVE
    ↓
mcuenv.py            build / flash / doctor 继承上述 shell 环境
    ↓
cmake toolchain      base-arm / cortex-m* 写 triplet 与 -mcpu；编译器从 PATH 解析
```

不用 mcuenv 时：把工程 `cmake/toolchain-*.cmake` 拷到固件仓库，自行把交叉编译链 `bin` 加入 PATH，即可裸跑 `cmake`（无需 `CC`/`CXX` 环境变量）。

## 配置说明

### 全局配置 `mcuenv.toml`

定义工具路径、默认烧录工具等。构建固定为 **CMake + Ninja**。路径相对于 `MCUENV_ROOT`（即本仓库根目录）。`[toolchain].prefix` 为保留字段；编译器 triplet 见 `cmake/toolchain-base-*.cmake`。

激活环境后，终端提示符会固定显示绿色粗体 `(mcuenv)` 前缀。

### 退出环境

激活后可在当前终端执行：

```bash
deactivate
mcuenv.py deactivate
```

也可以直接关闭终端。会恢复 PATH、相关环境变量和原始命令行提示符。

### 工程配置 `mcuenv.project.toml`

每个 firmware 工程一份，由 `set-target` 生成或手动编辑。工程根目录需存在该文件或 `CMakeLists.txt`，`mcuenv.py` 才能定位项目。

### CMake 交叉编译 toolchain（按 CPU 内核）

**按 ISA 分 base 文件**（工具 triplet + 通用 linker/section 逻辑）：

| 文件 | 用途 |
|------|------|
| `toolchain-base-arm.cmake` | `arm-none-eabi-gcc` 等；由 `toolchain-cortex-m*.cmake` include |
| `toolchain-base-riscv.cmake` | `riscv32-unknown-elf-gcc` 等；供后续 `toolchain-riscv*.cmake` profile 使用 |
| `toolchain-base.cmake` | 兼容旧引用，转发到 `toolchain-base-arm.cmake` |

`mcuenv.py build` 会根据 SQLite 芯片表里的 `cpu` 字段自动选择 profile：

| cpu | toolchain 文件 | 典型优化 |
|-----|----------------|----------|
| `cortex-m0` | `cmake/toolchain-cortex-m0.cmake` | 无 FPU |
| `cortex-m0plus` / `cortex-m0+` | `cmake/toolchain-cortex-m0plus.cmake` | 无 FPU |
| `cortex-m3` | `cmake/toolchain-cortex-m3.cmake` | 无 FPU |
| `cortex-m4` | `cmake/toolchain-cortex-m4.cmake` | FPv4-SP，hard float |
| `cortex-m7` | `cmake/toolchain-cortex-m7.cmake` | FPv5-SP，hard float |
| `cortex-m33` | `cmake/toolchain-cortex-m33.cmake` | FPv5-SP，hard float |

各文件均启用 `-ffunction-sections -fdata-sections` 与 `-Wl,--gc-sections`。未识别的 `cpu` 回退到 `mcuenv.toml` 里的 `cmake_toolchain_file`。

**`mcuenv.py build` 选用顺序：**

1. 工程 `mcuenv.project.toml` 的 `[build].toolchain_file`（相对工程根目录）
2. 否则按 `[project].target` → SQLite `cpu` → `mcu-env/cmake/toolchain-cortex-m*.cmake`
3. 否则 `mcuenv.toml` 的 fallback

可将 `toolchain-base-arm.cmake` 与对应的 `toolchain-cortex-m*.cmake` 拷入工程 `cmake/`（RISC-V 则用 `toolchain-base-riscv.cmake` + 后续 `toolchain-riscv*.cmake` profile）。编译器 triplet 写在各 ISA 的 base 文件里（如 `arm-none-eabi-gcc`），**由 PATH 解析**；`mcuenv-on` 只负责把 `mcuenv.toml` 里的工具目录 prepend 到 PATH。

**`mcuenv.py build` / `clean` / `flash` / `doctor` 均依赖当前终端环境**（子进程继承 shell，不再注入 env）。须先 `mcuenv-on`；`build`/`clean` 另外要求 PATH 上能找到 `arm-none-eabi-gcc`。

## 环境变量

激活环境后会设置：

| 变量 | 说明 |
|------|------|
| `MCUENV_ROOT` | 本环境根目录 |
| `PATH` | 追加 `bin/`、toolchain、cmake、ninja、openocd（**交叉编译器靠 PATH 找到**，不设 `CC`/`CXX`） |
| `OPENOCD_SCRIPTS` | OpenOCD 脚本目录 |
| `CMAKE_TOOLCHAIN_FILE` | 默认 ARM toolchain 文件（手动 cmake 时可选参考） |
| `MCUENV_ACTIVE` | 设为 `1` 表示已激活；`build`/`clean`/`flash`/`doctor` 会检查 |

交叉编译工具名按 ISA 写在 `cmake/toolchain-base-arm.cmake` / `toolchain-base-riscv.cmake` 里；`-mcpu` / `-march` 等由上层 profile（`toolchain-cortex-m*.cmake` 等）设置 `MCU_FLAGS` 后 include 对应 base。

## 贡献与发布

`tools/` 下各工具子目录（`arm-gnu-toolchain`、`cmake`、`ninja`、`openocd`、`pyocd`）、`packages/`、`manuals/`、`data/*.db` 默认不纳入版本控制。克隆仓库后本地安装工具并执行 `mcuenv.py registry init`。若团队需要共享二进制，可考虑 Git LFS、Release 附件或内部制品库。

变更记录见 [CHANGELOG.md](CHANGELOG.md)。

## 路线图

- [ ] 最小 blink 裸机工程模板
- [ ] CMSIS + RTOS 工程模板
- [ ] MCP Server（供 Cursor / Agent 调用 build / flash / doctor）
- [ ] `mcuenv new` 工程脚手架

## 许可证

- `mcuenv/` 及相关脚本：随本仓库约定使用
- `tools/` 内第三方工具（GCC、CMake、Ninja、OpenOCD 等）遵循各自上游许可证
