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


@dataclass
class ProjectConfig:
    root: Path
    name: str = "firmware"
    target: str = ""
    build_dir: str = "build"
    generator: str = ""
    flash_interface: str = ""
    openocd_target: str = ""
    openocd_interface: str = ""
    elf_name: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


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

    env_section = data.get("env", {})
    paths_section = data.get("paths", {})
    toolchain_section = data.get("toolchain", {})
    build_section = data.get("build", {})
    flash_section = data.get("flash", {})

    paths: dict[str, Path] = {}
    for key, value in paths_section.items():
        path = Path(value)
        if not path.is_absolute():
            path = env_root / path
        paths[key] = path

    toolchain_file = Path(toolchain_section.get("cmake_toolchain_file", ""))
    if not toolchain_file.is_absolute():
        toolchain_file = env_root / toolchain_file

    return GlobalConfig(
        root=env_root,
        paths=paths,
        toolchain_prefix=toolchain_section.get("prefix", "arm-none-eabi-"),
        cmake_toolchain_file=toolchain_file,
        build_generator=build_section.get("generator", "Ninja"),
        default_flash_interface=flash_section.get("default_interface", "stlink"),
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

    return ProjectConfig(
        root=root,
        name=project.get("name", "firmware"),
        target=project.get("target", ""),
        build_dir=build.get("build_dir", "build"),
        generator=build.get("generator", ""),
        flash_interface=flash.get("interface", ""),
        openocd_target=flash.get("openocd_target", ""),
        openocd_interface=flash.get("openocd_interface", ""),
        elf_name=build.get("elf_name", ""),
        extra=data,
    )


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

    lines.extend(
        [
            "",
            "[flash]",
        ]
    )
    if project.flash_interface:
        lines.append(f'interface = "{project.flash_interface}"')
    if project.openocd_target:
        lines.append(f'openocd_target = "{project.openocd_target}"')
    if project.openocd_interface:
        lines.append(f'openocd_interface = "{project.openocd_interface}"')

    config_path = project.root / PROJECT_CONFIG_NAME
    config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
