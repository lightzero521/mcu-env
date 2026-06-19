"""Environment detection and export."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from mcuenv.config import load_global_config
from mcuenv.util import exe_name, is_windows

MANAGED_ENV_VARS = (
    "OPENOCD_SCRIPTS",
    "CMAKE_TOOLCHAIN_FILE",
)


@dataclass(frozen=True)
class ToolPaths:
    toolchain: Path
    cmake: Path
    ninja: Path
    openocd: Path
    openocd_scripts: Path
    pyocd: Path | None = None


class EnvManager:
    def __init__(self, root: Path | None = None) -> None:
        self.config = load_global_config(root)
        self.tools = ToolPaths(
            toolchain=self.config.paths["toolchain"],
            cmake=self.config.paths["cmake"],
            ninja=self.config.paths["ninja"],
            openocd=self.config.paths["openocd"],
            openocd_scripts=self.config.paths["openocd_scripts"],
            pyocd=self.config.paths.get("pyocd"),
        )

    @property
    def root(self) -> Path:
        return self.config.root

    @property
    def bin_dir(self) -> Path:
        return self.root / "bin"

    def path_entries(self) -> list[Path]:
        entries = [self.bin_dir]
        entries.extend(
            [
                self.tools.toolchain,
                self.tools.cmake,
                self.tools.ninja,
                self.tools.openocd,
            ]
        )
        if self.tools.pyocd is not None:
            entries.append(self.tools.pyocd)
        return entries

    def mcuenv_env_values(self) -> dict[str, str]:
        return {
            "MCUENV_ROOT": str(self.root),
            "OPENOCD_SCRIPTS": str(self.tools.openocd_scripts),
            "CMAKE_TOOLCHAIN_FILE": str(self.config.cmake_toolchain_file),
        }

    def export_lines(self, fmt: str) -> list[str]:
        values = self.mcuenv_env_values()
        root = values["MCUENV_ROOT"]
        path_prefix = os.pathsep.join(str(path) for path in self.path_entries())

        if fmt in {"ps1", "powershell"}:
            lines = [f'$env:MCUENV_ROOT = "{root}"']
            for name in MANAGED_ENV_VARS:
                lines.append(f'$env:{name} = "{values[name]}"')
            lines.append(f'$env:PATH = "{path_prefix};$env:PATH"')
            return lines

        if fmt in {"bash", "sh"}:
            lines = [f'export MCUENV_ROOT="{root}"']
            for name in MANAGED_ENV_VARS:
                lines.append(f'export {name}="{values[name]}"')
            lines.append(f'export PATH="{path_prefix}:$PATH"')
            return lines

        raise ValueError(f"Unsupported export format: {fmt}")

    def _describe_jlink_dir(self) -> str:
        configured = self.config.paths.get("jlink")
        if configured is not None:
            return str(configured)
        from mcuenv.jlink import jlink_install_path_from_registry

        registry = jlink_install_path_from_registry()
        if registry is not None:
            return f"{registry} (registry)"
        return "(not configured; use PATH or set [paths].jlink)"

    @staticmethod
    def require_active_shell(*, require_cross_compiler: bool = False) -> str | None:
        if os.environ.get("MCUENV_ACTIVE") != "1":
            return (
                "mcuenv is not active. Run 'mcuenv-on' "
                "(or source export.ps1 / export.sh) first."
            )
        if require_cross_compiler and shutil.which("arm-none-eabi-gcc") is None:
            return (
                "arm-none-eabi-gcc was not found on PATH. "
                "Run 'mcuenv-on' to prepend toolchain paths from mcuenv.toml."
            )
        return None

    def tool_binary(self, name: str) -> Path:
        directory_map = {
            "cmake": self.tools.cmake,
            "ninja": self.tools.ninja,
            "openocd": self.tools.openocd,
            "pyocd": self.tools.pyocd,
            "arm-none-eabi-gcc": self.tools.toolchain,
            "arm-none-eabi-gdb": self.tools.toolchain,
            "arm-none-eabi-objcopy": self.tools.toolchain,
            "arm-none-eabi-size": self.tools.toolchain,
        }
        directory = directory_map.get(name, self.tools.toolchain)
        if directory is None:
            raise FileNotFoundError(f"Tool path is not configured: {name}")
        candidate = directory / exe_name(name)
        if candidate.is_file():
            return candidate
        raise FileNotFoundError(f"Tool not found: {candidate}")

    def describe(self) -> dict[str, str]:
        return {
            "root": str(self.root),
            "platform": "windows" if is_windows() else "unix",
            "toolchain_dir": str(self.tools.toolchain),
            "cmake_dir": str(self.tools.cmake),
            "ninja_dir": str(self.tools.ninja),
            "openocd_dir": str(self.tools.openocd),
            "openocd_scripts": str(self.tools.openocd_scripts),
            "pyocd_dir": str(self.tools.pyocd) if self.tools.pyocd else "(not configured)",
            "jlink_dir": self._describe_jlink_dir(),
            "cmake_toolchain_file": str(self.config.cmake_toolchain_file),
            "bin_dir": str(self.bin_dir),
        }
