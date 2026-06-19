"""Locate SEGGER J-Link Commander (JLinkExe / JLink)."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from mcuenv.util import exe_name, is_windows

# SEGGER documents both names for J-Link Commander on Windows.
COMMANDER_NAMES = ("JLinkExe", "JLink")


def _commander_in_dir(directory: Path) -> Path | None:
    for name in COMMANDER_NAMES:
        candidate = directory / exe_name(name)
        if candidate.is_file():
            return candidate.resolve()
    return None


def _commander_on_path() -> Path | None:
    found = shutil.which("JLinkExe")
    if found:
        return Path(found).resolve()

    found = shutil.which("JLink")
    if found and "segger" in found.replace("\\", "/").lower():
        return Path(found).resolve()
    return None


def jlink_install_path_from_registry() -> Path | None:
    if not is_windows():
        return None

    import winreg

    candidates = (
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\SEGGER\J-Link"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\SEGGER\J-Link"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\SEGGER\J-Link"),
    )
    for hive, subkey in candidates:
        try:
            with winreg.OpenKey(hive, subkey) as key:
                install_path, _ = winreg.QueryValueEx(key, "InstallPath")
        except OSError:
            continue
        if not install_path:
            continue
        path = Path(str(install_path))
        if path.is_dir():
            return path
    return None


def resolve_jlink_exe(
    configured_dir: Path | None = None,
) -> Path:
    """Resolve J-Link Commander: mcuenv.toml [paths].jlink, registry, then PATH."""
    search_dirs: list[Path] = []

    if configured_dir is not None:
        search_dirs.append(configured_dir)

    registry_dir = jlink_install_path_from_registry()
    if registry_dir is not None:
        search_dirs.append(registry_dir)

    for directory in search_dirs:
        candidate = _commander_in_dir(directory)
        if candidate is not None:
            return candidate

    from_path = _commander_on_path()
    if from_path is not None:
        return from_path

    hints = []
    if configured_dir is not None:
        hints.append(f"[paths].jlink ({configured_dir})")
    if registry_dir is not None:
        hints.append(f"registry InstallPath ({registry_dir})")
    checked = ", ".join(hints) if hints else "mcuenv.toml, registry"
    names = " / ".join(exe_name(name) for name in COMMANDER_NAMES)
    raise FileNotFoundError(
        f"J-Link Commander not found ({names}). Checked "
        f"{checked}, and PATH. Install SEGGER J-Link or set [paths].jlink in mcuenv.toml."
    )


def run_jlink_script(
    script_lines: list[str],
    *,
    configured_dir: Path | None = None,
    verbose: bool = False,
    progress: bool = False,
) -> int:
    from mcuenv.util import run_command

    jlink = resolve_jlink_exe(configured_dir)
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".jlink",
        delete=False,
        encoding="ascii",
        newline="\n",
    ) as handle:
        handle.write("\n".join(script_lines) + "\n")
        script_path = Path(handle.name)

    try:
        return run_command(
            [str(jlink), "-CommandFile", str(script_path)],
            verbose=verbose,
            progress=progress,
        )
    finally:
        script_path.unlink(missing_ok=True)
