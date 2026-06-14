"""Load global and project configuration."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


PROJECT_CONFIG_NAME = "mcuenv.project.toml"
GLOBAL_CONFIG_NAME = "mcuenv.toml"


@dataclass(frozen=True)
class GlobalConfig:
    root: Path
    paths: dict[str, Path]
    toolchain_prefix: str
    cmake_toolchain_file: Path
    build_generator: str
    default_flash_interface: str
    default_flash_probe: str
    default_flash_backend: str
    registry_database: Path | None = None


@dataclass
class ProjectConfig:
    root: Path
    name: str = "firmware"
    target: str = ""
    build_dir: str = "build"
    generator: str = ""
    elf_name: str = ""
    linker_script: str = ""
    toolchain_file: str = ""
    pre_build: list[str] = field(default_factory=list)
    post_build: list[str] = field(default_factory=list)
    flash_probe: str = ""
    flash_backend: str = ""
    flash_after_program: str = "reset_and_run"
    flash_interface: str = ""
    openocd_target: str = ""
    openocd_interface: str = ""
    jlink_device: str = ""
    pyocd_target: str = ""
    flash_speed: int = 0
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
    build_section = data.get("build", {})
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

    return GlobalConfig(
        root=env_root,
        paths=paths,
        toolchain_prefix=toolchain_section.get("prefix", "arm-none-eabi-"),
        cmake_toolchain_file=toolchain_file,
        build_generator=build_section.get("generator", "Ninja"),
        default_flash_interface=flash_section.get("default_interface", "stlink"),
        default_flash_probe=flash_section.get("default_probe", "stlink"),
        default_flash_backend=flash_section.get("default_backend", "openocd"),
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
    flash = data.get("flash", {})
    debug = data.get("debug", {})

    return ProjectConfig(
        root=root,
        name=project.get("name", "firmware"),
        target=project.get("target", ""),
        build_dir=build.get("build_dir", "build"),
        generator=build.get("generator", ""),
        elf_name=build.get("elf_name", ""),
        linker_script=build.get("linker_script", ""),
        toolchain_file=build.get("toolchain_file", ""),
        pre_build=_toml_string_list(build.get("pre_build")),
        post_build=_toml_string_list(build.get("post_build")),
        flash_probe=flash.get("probe", ""),
        flash_backend=flash.get("backend", ""),
        flash_after_program=flash.get("after_program", "reset_and_run"),
        flash_interface=flash.get("interface", ""),
        openocd_target=flash.get("openocd_target", ""),
        openocd_interface=flash.get("openocd_interface", ""),
        jlink_device=flash.get("jlink_device", ""),
        pyocd_target=flash.get("pyocd_target", ""),
        flash_speed=int(flash.get("speed", 0) or 0),
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
    project.flash_probe = preset.probe
    project.flash_backend = preset.backend
    project.openocd_target = preset.openocd_target
    project.openocd_interface = preset.openocd_interface or project.openocd_interface
    project.jlink_device = preset.jlink_device
    project.pyocd_target = preset.pyocd_target
    project.debug_probe = preset.probe
    project.debug_backend = preset.backend
    project.debug_jlink_device = preset.jlink_device
    project.debug_openocd_target = preset.openocd_target
    project.debug_openocd_interface = preset.openocd_interface
    project.debug_pyocd_target = preset.pyocd_target


def _append_toml_list(lines: list[str], key: str, values: list[str]) -> None:
    if not values:
        return
    if len(values) == 1:
        lines.append(f'{key} = "{values[0]}"')
        return
    items = ", ".join(f'"{value}"' for value in values)
    lines.append(f"{key} = [{items}]")


def write_project_config(project: ProjectConfig) -> None:
    lines = [
        "[project]",
        f'name = "{project.name}"',
        f'target = "{project.target}"',
        "",
        "[build]",
        f'build_dir = "{project.build_dir}"',
    ]

    if project.generator:
        lines.append(f'generator = "{project.generator}"')
    if project.elf_name:
        lines.append(f'elf_name = "{project.elf_name}"')
    if project.linker_script:
        lines.append(f'linker_script = "{project.linker_script}"')
    if project.toolchain_file:
        lines.append(f'toolchain_file = "{project.toolchain_file}"')
    _append_toml_list(lines, "pre_build", project.pre_build)
    _append_toml_list(lines, "post_build", project.post_build)

    lines.extend(["", "[flash]"])
    if project.flash_probe:
        lines.append(f'probe = "{project.flash_probe}"')
    if project.flash_backend:
        lines.append(f'backend = "{project.flash_backend}"')
    if project.flash_after_program:
        lines.append(f'after_program = "{project.flash_after_program}"')
    if project.flash_interface:
        lines.append(f'interface = "{project.flash_interface}"')
    if project.openocd_target:
        lines.append(f'openocd_target = "{project.openocd_target}"')
    if project.openocd_interface:
        lines.append(f'openocd_interface = "{project.openocd_interface}"')
    if project.jlink_device:
        lines.append(f'jlink_device = "{project.jlink_device}"')
    if project.pyocd_target:
        lines.append(f'pyocd_target = "{project.pyocd_target}"')
    if project.flash_speed:
        lines.append(f"speed = {project.flash_speed}")

    lines.extend(["", "[debug]"])
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
