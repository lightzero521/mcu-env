"""Flash helpers for OpenOCD, pyOCD, and J-Link backends."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from mcuenv.config import ProjectConfig, default_flash_image, load_project_config
from mcuenv.env import EnvManager
from mcuenv.flash_config import FlashSettings, resolve_flash_settings
from mcuenv.jlink import resolve_jlink_exe
from mcuenv.jlink_dll import JLinkDllError, run_jlink_flash
from mcuenv.registry_db import resolve_registry_paths
from mcuenv.targets import TargetPreset, get_target
from mcuenv.util import CommandTimer, run_command


def _registry_paths(env: EnvManager):
    return resolve_registry_paths(env.root, env.config.registry_database)


def _chip_preset(project: ProjectConfig, env: EnvManager) -> TargetPreset | None:
    if not project.target:
        return None
    return get_target(project.target, paths=_registry_paths(env))


def resolve_project_flash_settings(project: ProjectConfig, env: EnvManager) -> FlashSettings:
    preset = _chip_preset(project, env)
    return resolve_flash_settings(project, env.config, preset)


def _resolve_firmware(project: ProjectConfig, settings: FlashSettings) -> Path:
    pattern = settings.image.strip() or default_flash_image(project)
    base = project.root

    if any(character in pattern for character in "*?[]"):
        matches = sorted(path for path in base.glob(pattern) if path.is_file())
        if not matches:
            raise FileNotFoundError(f"No firmware file matched pattern: {base / pattern}")
        if len(matches) > 1:
            joined = ", ".join(str(path.relative_to(project.root)) for path in matches)
            raise FileNotFoundError(
                f"Multiple firmware files matched {pattern}: {joined}. "
                "Use a more specific [flash].image path."
            )
        return matches[0]

    firmware = base / pattern
    if not firmware.is_file():
        raise FileNotFoundError(
            f"Firmware image not found: {firmware}. Build the project first or set "
            "[flash].image in mcuenv.project.toml."
        )
    return firmware


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
    adapter: str | None,
    target: str | None,
    verbose: bool,
) -> int:
    openocd_cfg = settings.openocd
    resolved_adapter = adapter or openocd_cfg.adapter
    resolved_target = target or openocd_cfg.target
    openocd = manager.tool_binary("openocd")
    scripts = manager.tools.openocd_scripts

    command = [
        str(openocd),
        "-s",
        str(scripts),
        "-f",
        f"interface/{resolved_adapter}.cfg",
        "-f",
        f"target/{resolved_target}.cfg",
    ]
    if openocd_cfg.transport:
        command.extend(["-c", f"transport select {openocd_cfg.transport}"])
    if openocd_cfg.adapter_speed_khz > 0:
        command.extend(["-c", f"adapter speed {openocd_cfg.adapter_speed_khz}"])
    if openocd_cfg.extra_commands:
        command.extend(["-c", openocd_cfg.extra_commands])
    command.extend(
        ["-c", _openocd_program_command(settings.after_program, firmware)]
    )
    return run_command(command, verbose=verbose, progress=True)


def find_pyocd(manager: EnvManager) -> str:
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


def find_jlink(manager: EnvManager) -> Path:
    return resolve_jlink_exe(manager.config.paths.get("jlink"))


def _flash_pyocd(
    settings: FlashSettings,
    firmware: Path,
    manager: EnvManager,
    *,
    target: str | None,
    verbose: bool,
) -> int:
    pyocd = find_pyocd(manager)
    pyocd_cfg = settings.pyocd
    resolved_target = target or pyocd_cfg.target
    command = [
        pyocd,
        "flash",
        "-t",
        resolved_target,
        "-f",
        str(pyocd_cfg.frequency_hz),
        str(firmware),
    ]
    if pyocd_cfg.probe_uid:
        command.extend(["-u", pyocd_cfg.probe_uid])
    if pyocd_cfg.pack:
        command.extend(["--pack", pyocd_cfg.pack])
    if settings.after_program == "none":
        command.append("--no-reset")
    return run_command(command, verbose=verbose, progress=True)


def _flash_jlink(
    settings: FlashSettings,
    firmware: Path,
    manager: EnvManager,
    *,
    verbose: bool,
) -> int:
    if verbose:
        jlink = settings.jlink
        print(
            f"J-Link flash: device={jlink.device}, interface={jlink.interface}, "
            f"speed={jlink.speed_khz} kHz, ip={jlink.ip or '(local USB)'}, "
            f"image={firmware}",
            flush=True,
        )
    try:
        run_jlink_flash(
            settings.jlink,
            firmware,
            configured_dir=manager.config.paths.get("jlink"),
            after_program=settings.after_program,
        )
    except (JLinkDllError, FileNotFoundError, OSError) as exc:
        print(f"J-Link flash failed: {exc}", file=sys.stderr)
        return 1
    return 0


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

    with CommandTimer("Flash"):
        project = load_project_config(project_dir)
        settings = resolve_project_flash_settings(project, manager)
        firmware = elf or _resolve_firmware(project, settings)

        if settings.tool == "openocd":
            return _flash_openocd(
                settings,
                firmware,
                manager,
                adapter=interface,
                target=target,
                verbose=verbose,
            )
        if settings.tool == "pyocd":
            return _flash_pyocd(
                settings,
                firmware,
                manager,
                target=target,
                verbose=verbose,
            )
        if settings.tool == "jlink":
            return _flash_jlink(settings, firmware, manager, verbose=verbose)

        raise ValueError(f"Unsupported flash tool: {settings.tool}")


def describe_flash_settings(project: ProjectConfig, env: EnvManager) -> dict[str, str]:
    settings = resolve_project_flash_settings(project, env)
    preset = _chip_preset(project, env)

    return {
        "project": project.name,
        "target": project.target or "(unset)",
        "mcu": preset.mcu if preset else "(unset)",
        "probe": settings.probe,
        "tool": settings.tool,
        "after_program": settings.after_program,
        "image": settings.image or default_flash_image(project),
        "jlink_device": settings.jlink.device,
        "jlink_interface": settings.jlink.interface,
        "jlink_speed_khz": str(settings.jlink.speed_khz),
        "jlink_ip": settings.jlink.ip or "(local USB)",
        "openocd_adapter": settings.openocd.adapter,
        "openocd_target": settings.openocd.target,
        "pyocd_target": settings.pyocd.target,
    }
