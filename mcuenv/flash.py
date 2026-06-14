"""Flash helpers for OpenOCD, pyOCD, and J-Link backends."""

from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from mcuenv.config import ProjectConfig, load_project_config
from mcuenv.env import EnvManager
from mcuenv.registry_db import resolve_registry_paths
from mcuenv.targets import TargetPreset, get_target
from mcuenv.util import run_command


@dataclass(frozen=True)
class FlashSettings:
    probe: str
    backend: str
    after_program: str
    openocd_interface: str
    openocd_target: str
    jlink_device: str
    pyocd_target: str
    speed: int


def _registry_paths(env: EnvManager):
    return resolve_registry_paths(env.root, env.config.registry_database)


def _chip_preset(project: ProjectConfig, env: EnvManager) -> TargetPreset | None:
    if not project.target:
        return None
    return get_target(project.target, paths=_registry_paths(env))


def _resolve_flash_settings(project: ProjectConfig, env: EnvManager) -> FlashSettings:
    preset = _chip_preset(project, env)

    probe = project.flash_probe or (preset.probe if preset else "") or env.config.default_flash_probe
    backend = (
        project.flash_backend
        or (preset.backend if preset else "")
        or env.config.default_flash_backend
    )

    openocd_interface = (
        project.openocd_interface
        or project.flash_interface
        or (preset.openocd_interface if preset else "")
        or env.config.default_flash_interface
    )
    openocd_target = project.openocd_target or (preset.openocd_target if preset else "")
    jlink_device = project.jlink_device or (preset.jlink_device if preset else "")
    pyocd_target = project.pyocd_target or (preset.pyocd_target if preset else "")

    if backend == "openocd" and not openocd_target:
        raise ValueError(
            "OpenOCD target is not configured. Run 'mcuenv.py set-target <name>' "
            "or set [flash].openocd_target in mcuenv.project.toml."
        )
    if backend == "pyocd" and not pyocd_target:
        raise ValueError(
            "pyOCD target is not configured. Set [flash].pyocd_target in mcuenv.project.toml."
        )
    if backend == "jlink" and not jlink_device:
        raise ValueError(
            "J-Link device is not configured. Set [flash].jlink_device in mcuenv.project.toml."
        )

    return FlashSettings(
        probe=probe,
        backend=backend,
        after_program=project.flash_after_program or "reset_and_run",
        openocd_interface=openocd_interface,
        openocd_target=openocd_target,
        jlink_device=jlink_device,
        pyocd_target=pyocd_target,
        speed=project.flash_speed,
    )


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


def _openocd_program_command(
    after_program: str,
    firmware: Path,
) -> str:
    if after_program == "none":
        return f"program {firmware.as_posix()} verify exit"
    if after_program == "reset_halt":
        return f"program {firmware.as_posix()} verify reset halt exit"
    return f"program {firmware.as_posix()} verify reset exit"


def _flash_openocd(
    settings: FlashSettings,
    firmware: Path,
    manager: EnvManager,
    *,
    interface: str | None,
    target: str | None,
    verbose: bool,
) -> int:
    resolved_interface = interface or settings.openocd_interface
    resolved_target = target or settings.openocd_target
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
        _openocd_program_command(settings.after_program, firmware),
    ]
    return run_command(command, verbose=verbose)


def _find_pyocd(manager: EnvManager) -> str:
    if manager.tools.pyocd is not None:
        try:
            return str(manager.tool_binary("pyocd"))
        except FileNotFoundError:
            pass

    pyocd = shutil.which("pyocd")
    if pyocd:
        return pyocd
    raise FileNotFoundError(
        "pyOCD not found. Configure [paths].pyocd in mcuenv.toml or install with: "
        "python -m pip install pyocd"
    )


def _flash_pyocd(
    settings: FlashSettings,
    firmware: Path,
    manager: EnvManager,
    *,
    target: str | None,
    verbose: bool,
) -> int:
    pyocd = _find_pyocd(manager)
    resolved_target = target or settings.pyocd_target
    command = [pyocd, "flash", "-t", resolved_target, str(firmware)]
    if settings.after_program == "none":
        command.append("--no-reset")
    return run_command(command, verbose=verbose)


def _flash_jlink(
    settings: FlashSettings,
    firmware: Path,
    *,
    verbose: bool,
) -> int:
    jlink = shutil.which("JLinkExe")
    if not jlink:
        raise FileNotFoundError(
            "JLinkExe not found in PATH. Install SEGGER J-Link software first."
        )

    reset_line = "r"
    if settings.after_program == "none":
        reset_line = ""
    elif settings.after_program == "reset_halt":
        reset_line = "r\nhalt"

    script_lines = [
        f"device {settings.jlink_device}",
        "si SWD",
        f"speed {settings.speed or 4000}",
        "connect",
        f"loadfile {firmware}",
        "verify",
    ]
    if reset_line:
        script_lines.append(reset_line)
    script_lines.append("exit")

    script_path = firmware.parent / ".mcuenv_jlink_flash.jlink"
    script_path.write_text("\n".join(script_lines) + "\n", encoding="ascii")
    try:
        return run_command([jlink, "-CommandFile", str(script_path)], verbose=verbose)
    finally:
        script_path.unlink(missing_ok=True)


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
    activation_error = EnvManager.require_active_shell()
    if activation_error:
        print(activation_error, file=sys.stderr)
        return 1

    project = load_project_config(project_dir)
    settings = _resolve_flash_settings(project, manager)
    firmware = elf or _resolve_elf(project)

    if settings.backend == "openocd":
        return _flash_openocd(
            settings,
            firmware,
            manager,
            interface=interface,
            target=target,
            verbose=verbose,
        )
    if settings.backend == "pyocd":
        return _flash_pyocd(
            settings,
            firmware,
            manager,
            target=target,
            verbose=verbose,
        )
    if settings.backend == "jlink":
        return _flash_jlink(settings, firmware, verbose=verbose)

    raise ValueError(f"Unsupported flash backend: {settings.backend}")


def describe_flash_settings(project: ProjectConfig, env: EnvManager) -> dict[str, str]:
    settings = _resolve_flash_settings(project, env)
    preset = _chip_preset(project, env)

    return {
        "project": project.name,
        "target": project.target or "(unset)",
        "mcu": preset.mcu if preset else "(unset)",
        "probe": settings.probe,
        "backend": settings.backend,
        "after_program": settings.after_program,
        "openocd_interface": settings.openocd_interface,
        "openocd_target": settings.openocd_target,
        "jlink_device": settings.jlink_device,
        "pyocd_target": settings.pyocd_target,
    }
