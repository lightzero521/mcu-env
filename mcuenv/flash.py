"""OpenOCD flash helpers."""

from __future__ import annotations

from pathlib import Path

from mcuenv.config import ProjectConfig, load_project_config
from mcuenv.env import EnvManager
from mcuenv.targets import TargetPreset, get_target
from mcuenv.util import run_command


def _resolve_flash_settings(
    project: ProjectConfig,
    env: EnvManager,
) -> tuple[str, str]:
    interface = (
        project.openocd_interface
        or project.flash_interface
        or env.config.default_flash_interface
    )

    if project.openocd_target:
        target = project.openocd_target
    elif project.target:
        target = get_target(project.target).openocd_target
    else:
        raise ValueError(
            "Flash target is not configured. Run 'mcuenv.py set-target <name>' "
            "or set [flash].openocd_target in mcuenv.project.toml."
        )

    return interface, target


def _resolve_elf(project: ProjectConfig) -> Path:
    if project.elf_name:
        elf = project.root / project.elf_name
    else:
        elf = project.root / project.build_dir / f"{project.name}.elf"

    if not elf.is_file():
        raise FileNotFoundError(
            f"Firmware image not found: {elf}. Build the project first or set "
            "[build].elf_name in mcuenv.project.toml."
        )
    return elf


def flash_project(
    project_dir: Path | None = None,
    *,
    interface: str | None = None,
    target: str | None = None,
    elf: Path | None = None,
    verbose: bool = False,
    env: EnvManager | None = None,
) -> int:
    manager = env or EnvManager()
    project = load_project_config(project_dir)
    resolved_interface, resolved_target = _resolve_flash_settings(project, manager)

    if interface:
        resolved_interface = interface
    if target:
        resolved_target = target

    firmware = elf or _resolve_elf(project)
    openocd = manager.tool_binary("openocd")
    scripts = manager.tools.openocd_scripts

    command = [
        str(openocd),
        "-s",
        str(scripts),
        "-f",
        f"interface/{resolved_interface}.cfg",
        "-f",
        f"target/{resolved_target}.cfg",
        "-c",
        f"program {firmware.as_posix()} verify reset exit",
    ]
    return run_command(command, env=manager.as_dict(), verbose=verbose)


def describe_flash_settings(project: ProjectConfig, env: EnvManager) -> dict[str, str]:
    interface, openocd_target = _resolve_flash_settings(project, env)
    preset: TargetPreset | None = None
    if project.target:
        preset = get_target(project.target)

    return {
        "project": project.name,
        "target": project.target or "(unset)",
        "mcu": preset.mcu if preset else "(unset)",
        "openocd_interface": interface,
        "openocd_target": openocd_target,
    }
