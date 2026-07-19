# Changelog

本文件记录 mcu-env 的重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

## [Unreleased]

### Added

- `mcuenv.py fullclean`：删除整个 `[build].build_dir`（含 CMake 缓存），行为对齐 ESP-IDF `idf.py fullclean`；`clean` 仍为 `cmake --build --target clean`。
- `mcuenv.py build --debug` / `--release`：覆盖 `[build].build_type`，传入 `-DCMAKE_BUILD_TYPE`（默认读 TOML）。
- 工程 `mcuenv.project.toml` 分 backend 的 `[flash]` / `[flash.jlink]` / `[flash.openocd]` / `[flash.pyocd]` 配置（`flash_config.py`）。
- J-Link 烧录/擦除：`jlink_dll.py` 通过 ctypes 调用 SEGGER DLL（`JLINK_DownloadFile`、`JLINK_EraseChip`），烧录/擦除进度条来自 DLL 回调。
- `[flash.jlink].ip`：连接 J-Link Remote Server（`host` 或 `host:port`，默认端口 19020）；空字符串仍用本地 USB。
- `mcuenv.py erase`：支持 pyOCD（`erase --chip`）与 J-Link（整片擦除）。
- `mcuenv.py -v` / `--verbose`：`build` 时对 `cmake --build` 加 `--verbose`；编译输出 Keil 风格（`compiling foo.c`），隐藏完整 gcc 命令行；`clean` 打印执行的 cmake 命令。
- `set-target` 写出完整 `[build]` 模板与 `[flash].image`（默认 `build/<项目名>.elf`）。

### Changed

- **构建**：固定 **CMake + Ninja**（移除工程级 generator / Make 选项）；`build` 默认透传 Ninja `[n/m]` 行，不再用单行进度条吞掉 POST_BUILD（如 `size`）输出。
- **J-Link DLL**：64 位 Python 优先加载 `JLink_x64.dll`，32 位使用 `JLinkARM.dll`；架构不匹配时给出明确错误。
- **Flash**：OpenOCD / pyOCD / J-Link 统一走 `FlashSettings` 解析；J-Link 不再依赖 `JLink.exe` 脚本烧录（Commander 解析仍用于 `doctor` 等）。
- 工程配置：`elf_name` 迁移为 `[flash].image`；`toolchain_file` / `linker_script` 留空时的 fallback 行为与文档对齐。

### Fixed

- J-Link 进度回调：`action` / `progress_string` 为 `NULL` 时不再崩溃；取消回调使用空函数而非 `None`（避免 ctypes `ArgumentError`）。
- `--verbose build`：适配 Ninja 将完整 gcc 命令与 `[n/m]` 打在同一行的输出格式。
- `erase` / `flash`（J-Link）：捕获 `OSError`（含 DLL 位数不匹配）并打印友好错误。
- **Linux / Bash**：`mcuenv-on` 提示符前缀改用 `\e`（Bash `PS1` 不解析 `\x1b`，此前会显示乱码）。
- **Linux / Bash**：`export.sh` 激活结束后恢复 `errexit` / `nounset` / `pipefail`，避免 `mcuenv.py doctor` 等有失败项时退出码为 1 导致整个终端会话退出。
- **Linux / Bash**：`export.sh` 在 `PS1` 未设置时不再因 `nounset` 报错；`bin/mcuenv.py` 启动器增加可执行权限。

### Notes

- `[debug]` 段仍会由 `set-target` 写入，**当前 CLI 尚未实现调试服务器**，不影响 `build` / `flash` / `erase`。
- Windows PowerShell 下请使用 `mcuenv.py --verbose build`；单独 `-v` 会被 PowerShell 当作 `-Verbose` 吞掉（`export.ps1` 包装函数限制）。

## [0.1.0] - 2025-06-01

### Added

- 便携式 MCU 环境：`mcuenv-on`、CMake toolchain、SQLite registry、多 backend flash 初版、Web 管理后台等（见 `c3f5cb3`）。

[Unreleased]: https://github.com/lightzero521/mcu-env/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/lightzero521/mcu-env/releases/tag/v0.1.0
