"""Erase flash via pyOCD or J-Link."""

from __future__ import annotations

import sys
from pathlib import Path

from mcuenv.config import load_project_config
from mcuenv.env import EnvManager
from mcuenv.flash import find_pyocd, resolve_project_flash_settings
from mcuenv.flash_config import FlashSettings
from mcuenv.jlink_dll import JLinkDllError, run_jlink_erase
from mcuenv.util import CommandTimer, run_command


def _erase_pyocd(
    settings: FlashSettings,
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
        "erase",
        "--chip",
        "-t",
        resolved_target,
        "-f",
        str(pyocd_cfg.frequency_hz),
    ]
    if pyocd_cfg.probe_uid:
        command.extend(["-u", pyocd_cfg.probe_uid])
    return run_command(command, verbose=verbose, progress=True)


def _erase_jlink(
    settings: FlashSettings,
    manager: EnvManager,
    *,
    verbose: bool,
) -> int:
    if verbose:
        jlink = settings.jlink
        print(
            f"J-Link erase: device={jlink.device}, interface={jlink.interface}, "
            f"speed={jlink.speed_khz} kHz, ip={jlink.ip or '(local USB)'}",
            flush=True,
        )
    try:
        run_jlink_erase(
            settings.jlink,
            configured_dir=manager.config.paths.get("jlink"),
        )
    except (JLinkDllError, FileNotFoundError, OSError) as exc:
        print(f"J-Link erase failed: {exc}", file=sys.stderr)
        return 1
    return 0


def erase_project(
    project_dir: Path | None = None,
    *,
    target: str | None = None,
    verbose: bool = False,
    env: EnvManager | None = None,
) -> int:
    manager = env or EnvManager()
    activation_error = EnvManager.require_active_shell()
    if activation_error:
        print(activation_error, file=sys.stderr)
        return 1

    with CommandTimer("Erase"):
        project = load_project_config(project_dir)
        settings = resolve_project_flash_settings(project, manager)

        if settings.tool == "pyocd":
            return _erase_pyocd(settings, manager, target=target, verbose=verbose)
        if settings.tool == "jlink":
            return _erase_jlink(settings, manager, verbose=verbose)

        raise ValueError(
            f"Erase is not supported for tool '{settings.tool}'. "
            "Use pyocd or jlink in [flash].tool."
        )
