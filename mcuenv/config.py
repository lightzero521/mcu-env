"""Load global and project configuration."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mcuenv.flash_config import (
    FlashJlinkConfig,
    FlashOpenocdConfig,
    FlashPyocdConfig,
    default_jlink_config,
    default_openocd_config,
    default_pyocd_config,
    jlink_config_from_mapping,
    jlink_config_from_preset,
    migrate_legacy_flash_section,
    openocd_config_from_mapping,
    openocd_config_from_preset,
    pyocd_config_from_mapping,
    pyocd_config_from_preset,
)


PROJECT_CONFIG_NAME = "mcuenv.project.toml"
GLOBAL_CONFIG_NAME = "mcuenv.toml"


def default_flash_image(project: ProjectConfig) -> str:
    """Default firmware path relative to project root when [flash].image is empty."""
    return f"{project.build_dir}/{project.name}.elf"


@dataclass(frozen=True)
class GlobalConfig:
    root: Path
    paths: dict[str, Path]
    toolchain_prefix: str
    cmake_toolchain_file: Path
    default_flash_tool: str
    default_flash_probe: str
    registry_database: Path | None = None


@dataclass
class ProjectConfig:
    root: Path
    name: str = "firmware"
    target: str = ""
    build_dir: str = "build"
    linker_script: str = ""
    toolchain_file: str = ""
    pre_build: list[str] = field(default_factory=list)
    post_build: list[str] = field(default_factory=list)
    flash_tool: str = ""
    flash_probe: str = ""
    flash_after_program: str = "reset_and_run"
    flash_image: str = ""
    flash_jlink: FlashJlinkConfig = field(default_factory=default_jlink_config)
    flash_openocd: FlashOpenocdConfig = field(default_factory=default_openocd_config)
    flash_pyocd: FlashPyocdConfig = field(default_factory=default_pyocd_config)
    debug_probe: str = ""
    debug_backend: str = ""
    debug_on_connect: str = "reset_halt"
    debug_gdb_port: int = 0
    debug_jlink_device: str = ""
    debug_openocd_target: str = ""
    debug_openocd_interface: str = ""
    debug_pyocd_target: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


def _toml_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def detect_root(start: Path | None = None) -> Path:
    if start is None:
        start = Path(__file__).resolve().parent.parent
    else:
        start = start.resolve()

    if (start / GLOBAL_CONFIG_NAME).is_file():
        return start

    current = start
    for _ in range(8):
        if (current / GLOBAL_CONFIG_NAME).is_file():
            return current
        if current.parent == current:
            break
        current = current.parent

    return Path(__file__).resolve().parent.parent


def load_global_config(root: Path | None = None) -> GlobalConfig:
    env_root = detect_root(root)
    config_path = env_root / GLOBAL_CONFIG_NAME
    if not config_path.is_file():
        raise FileNotFoundError(f"Missing global config: {config_path}")

    with config_path.open("rb") as handle:
        data = tomllib.load(handle)

    paths_section = data.get("paths", {})
    toolchain_section = data.get("toolchain", {})
    flash_section = data.get("flash", {})
    registry_section = data.get("registry", {})

    paths: dict[str, Path] = {}
    for key, value in paths_section.items():
        path = Path(value)
        if not path.is_absolute():
            path = env_root / path
        paths[key] = path

    toolchain_file = Path(toolchain_section.get("cmake_toolchain_file", ""))
    if not toolchain_file.is_absolute():
        toolchain_file = env_root / toolchain_file

    registry_database: Path | None = None
    registry_db_value = registry_section.get("database")
    if registry_db_value:
        registry_database = Path(registry_db_value)
        if not registry_database.is_absolute():
            registry_database = env_root / registry_database

    default_tool = flash_section.get("default_tool") or flash_section.get("default_backend", "openocd")

    return GlobalConfig(
        root=env_root,
        paths=paths,
        toolchain_prefix=toolchain_section.get("prefix", "arm-none-eabi-"),
        cmake_toolchain_file=toolchain_file,
        default_flash_tool=default_tool,
        default_flash_probe=flash_section.get("default_probe", "stlink"),
        registry_database=registry_database,
    )


def find_project_root(start: Path | None = None) -> Path:
    current = Path.cwd() if start is None else start.resolve()
    markers = (PROJECT_CONFIG_NAME, "CMakeLists.txt")

    for directory in [current, *current.parents]:
        if any((directory / marker).is_file() for marker in markers):
            return directory

    raise FileNotFoundError(
        "No MCU project found. Expected mcuenv.project.toml or CMakeLists.txt "
        f"in {current} or a parent directory."
    )


def load_project_config(project_root: Path | None = None) -> ProjectConfig:
    root = find_project_root(project_root)
    config_path = root / PROJECT_CONFIG_NAME

    if not config_path.is_file():
        return ProjectConfig(root=root)

    with config_path.open("rb") as handle:
        data = tomllib.load(handle)

    project = data.get("project", {})
    build = data.get("build", {})
    flash = migrate_legacy_flash_section(data.get("flash", {}))
    debug = data.get("debug", {})

    flash_image = str(flash.get("image", ""))
    legacy_elf = build.get("elf_name", "")
    if not flash_image and legacy_elf:
        flash_image = str(legacy_elf)

    return ProjectConfig(
        root=root,
        name=project.get("name", "firmware"),
        target=project.get("target", ""),
        build_dir=build.get("build_dir", "build"),
        linker_script=str(build.get("linker_script", "")),
        toolchain_file=str(build.get("toolchain_file", "")),
        pre_build=_toml_string_list(build.get("pre_build")),
        post_build=_toml_string_list(build.get("post_build")),
        flash_tool=str(flash.get("tool", "")),
        flash_probe=str(flash.get("probe", "")),
        flash_after_program=str(flash.get("after_program", "reset_and_run")),
        flash_image=flash_image,
        flash_jlink=jlink_config_from_mapping(flash.get("jlink")),
        flash_openocd=openocd_config_from_mapping(flash.get("openocd")),
        flash_pyocd=pyocd_config_from_mapping(flash.get("pyocd")),
        debug_probe=debug.get("probe", ""),
        debug_backend=debug.get("backend", ""),
        debug_on_connect=debug.get("on_connect", "reset_halt"),
        debug_gdb_port=int(debug.get("gdb_port", 0) or 0),
        debug_jlink_device=debug.get("jlink_device", ""),
        debug_openocd_target=debug.get("openocd_target", ""),
        debug_openocd_interface=debug.get("openocd_interface", ""),
        debug_pyocd_target=debug.get("pyocd_target", ""),
        extra=data,
    )


def apply_target_defaults(project: ProjectConfig, preset) -> None:
    project.target = preset.name
    project.toolchain_file = ""
    project.linker_script = ""
    project.pre_build = []
    project.post_build = []
    project.flash_tool = preset.tool
    project.flash_probe = preset.probe
    project.flash_after_program = "reset_and_run"
    project.flash_jlink = jlink_config_from_preset(preset)
    project.flash_openocd = openocd_config_from_preset(preset)
    project.flash_pyocd = pyocd_config_from_preset(preset)
    project.debug_probe = preset.probe
    project.debug_backend = preset.backend
    project.debug_jlink_device = preset.jlink_device
    project.debug_openocd_target = preset.openocd_target
    project.debug_openocd_interface = preset.openocd_interface
    project.debug_pyocd_target = preset.pyocd_target


def _format_toml_list(values: list[str]) -> str:
    if not values:
        return "[]"
    if len(values) == 1:
        return f'["{values[0]}"]'
    items = ", ".join(f'"{value}"' for value in values)
    return f"[{items}]"


def write_project_config(project: ProjectConfig) -> None:
    jlink = project.flash_jlink
    openocd = project.flash_openocd
    pyocd = project.flash_pyocd

    lines = [
        "[project]",
        f'name = "{project.name}"',
        f'target = "{project.target}"',
        "",
        "[build]",
        "# CMake 构建输出目录",
        f'build_dir = "{project.build_dir}"',
        "# 工程 toolchain（相对工程根）；留空则按 chip cpu 或 mcuenv.toml fallback",
        f'toolchain_file = "{project.toolchain_file}"',
        "# 链接脚本（相对工程根）；留空则不注入，由 CMakeLists 指定",
        f'linker_script = "{project.linker_script}"',
        "# 编译前脚本（相对工程根）；空列表表示不执行",
        f"pre_build = {_format_toml_list(project.pre_build)}",
        "# 编译后脚本；空列表表示不执行",
        f"post_build = {_format_toml_list(project.post_build)}",
        "",
        "[flash]",
        "# 烧录软件栈：openocd | pyocd | jlink",
        f'tool = "{project.flash_tool}"',
        "# 物理调试探针：stlink | jlink | cmsis-dap",
        f'probe = "{project.flash_probe}"',
        "# 烧录完成后：reset_and_run | reset_halt | none",
        f'after_program = "{project.flash_after_program}"',
        "# 烧录固件（相对工程根，支持 glob）；留空则使用 build_dir/<项目名>.elf",
        f'image = "{project.flash_image}"',
        "",
        "[flash.jlink]",
        "# J-Link 设备名（SEGGER 设备数据库）",
        f'device = "{jlink.device}"',
        "# 调试接口：swd | jtag",
        f'interface = "{jlink.interface}"',
        "# 连接速度（kHz）",
        f"speed_khz = {jlink.speed_khz}",
        "# J-Link 序列号；空字符串表示自动选择",
        f'serial = "{jlink.serial}"',
        "# 复位策略（可选），如 connect_under_reset",
        f'reset_strategy = "{jlink.reset_strategy}"',
        "# J-Link 脚本文件（可选）",
        f'script = "{jlink.script}"',
        "",
        "[flash.openocd]",
        "# 适配器配置名（interface/<adapter>.cfg）",
        f'adapter = "{openocd.adapter}"',
        "# 目标配置名（target/<target>.cfg）",
        f'target = "{openocd.target}"',
        "# 传输协议：swd | jtag",
        f'transport = "{openocd.transport}"',
        "# 适配器速度（kHz）；0 表示默认",
        f"adapter_speed_khz = {openocd.adapter_speed_khz}",
        "# 额外 OpenOCD -c 命令（可选）",
        f'extra_commands = "{openocd.extra_commands}"',
        "",
        "[flash.pyocd]",
        "# pyOCD 目标名",
        f'target = "{pyocd.target}"',
        "# 探针 UID；空字符串表示自动选择",
        f'probe_uid = "{pyocd.probe_uid}"',
        "# SWD 频率（Hz）",
        f"frequency_hz = {pyocd.frequency_hz}",
        "# 连接方式（可选）",
        f'connect_mode = "{pyocd.connect_mode}"',
        "# 自定义 CMSIS-Pack 路径（可选）",
        f'pack = "{pyocd.pack}"',
        "",
        "[debug]",
    ]

    if project.debug_probe:
        lines.append(f'probe = "{project.debug_probe}"')
    if project.debug_backend:
        lines.append(f'backend = "{project.debug_backend}"')
    if project.debug_on_connect:
        lines.append(f'on_connect = "{project.debug_on_connect}"')
    if project.debug_gdb_port:
        lines.append(f"gdb_port = {project.debug_gdb_port}")
    if project.debug_jlink_device:
        lines.append(f'jlink_device = "{project.debug_jlink_device}"')
    if project.debug_openocd_target:
        lines.append(f'openocd_target = "{project.debug_openocd_target}"')
    if project.debug_openocd_interface:
        lines.append(f'openocd_interface = "{project.debug_openocd_interface}"')
    if project.debug_pyocd_target:
        lines.append(f'pyocd_target = "{project.debug_pyocd_target}"')

    config_path = project.root / PROJECT_CONFIG_NAME
    config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
