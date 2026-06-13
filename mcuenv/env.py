"""Environment detection and export."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from mcuenv.config import load_global_config
from mcuenv.util import exe_name, is_windows


@dataclass(frozen=True)
class ToolPaths:
    toolchain: Path
    cmake: Path
    ninja: Path
    openocd: Path
    openocd_scripts: Path


class EnvManager:
    def __init__(self, root: Path | None = None) -> None:
        self.config = load_global_config(root)
        self.tools = ToolPaths(
            toolchain=self.config.paths["toolchain"],
            cmake=self.config.paths["cmake"],
            ninja=self.config.paths["ninja"],
            openocd=self.config.paths["openocd"],
            openocd_scripts=self.config.paths["openocd_scripts"],
        )

    @property
    def root(self) -> Path:
        return self.config.root

    def path_entries(self) -> list[Path]:
        return [
            self.tools.toolchain,
            self.tools.cmake,
            self.tools.ninja,
            self.tools.openocd,
        ]

    def as_dict(self) -> dict[str, str]:
        prefix = self.config.toolchain_prefix.rstrip("-")
        if not prefix.endswith("-"):
            prefix = f"{prefix}-"

        env = os.environ.copy()
        env["MCUENV_ROOT"] = str(self.root)
        env["OPENOCD_SCRIPTS"] = str(self.tools.openocd_scripts)
        env["CMAKE_TOOLCHAIN_FILE"] = str(self.config.cmake_toolchain_file)
        env["CROSS_COMPILE"] = prefix
        env["CC"] = f"{prefix}gcc"
        env["CXX"] = f"{prefix}g++"
        env["AR"] = f"{prefix}ar"
        env["OBJCOPY"] = f"{prefix}objcopy"
        env["SIZE"] = f"{prefix}size"
        env["PATH"] = os.pathsep.join(
            [*(str(path) for path in self.path_entries()), env.get("PATH", "")]
        )
        return env

    def export_lines(self, fmt: str) -> list[str]:
        env = self.as_dict()
        root = env["MCUENV_ROOT"]

        if fmt in {"ps1", "powershell"}:
            return [
                f'$env:MCUENV_ROOT = "{root}"',
                f'$env:OPENOCD_SCRIPTS = "{env["OPENOCD_SCRIPTS"]}"',
                f'$env:CMAKE_TOOLCHAIN_FILE = "{env["CMAKE_TOOLCHAIN_FILE"]}"',
                f'$env:CROSS_COMPILE = "{env["CROSS_COMPILE"]}"',
                f'$env:CC = "{env["CC"]}"',
                f'$env:CXX = "{env["CXX"]}"',
                f'$env:PATH = "{os.pathsep.join(str(path) for path in self.path_entries())};$env:PATH"',
            ]

        if fmt in {"bash", "sh"}:
            path_entries = os.pathsep.join(str(path) for path in self.path_entries())
            return [
                f'export MCUENV_ROOT="{root}"',
                f'export OPENOCD_SCRIPTS="{env["OPENOCD_SCRIPTS"]}"',
                f'export CMAKE_TOOLCHAIN_FILE="{env["CMAKE_TOOLCHAIN_FILE"]}"',
                f'export CROSS_COMPILE="{env["CROSS_COMPILE"]}"',
                f'export CC="{env["CC"]}"',
                f'export CXX="{env["CXX"]}"',
                f'export PATH="{path_entries}:$PATH"',
            ]

        raise ValueError(f"Unsupported export format: {fmt}")

    def tool_binary(self, name: str) -> Path:
        directory_map = {
            "cmake": self.tools.cmake,
            "ninja": self.tools.ninja,
            "openocd": self.tools.openocd,
            "arm-none-eabi-gcc": self.tools.toolchain,
            "arm-none-eabi-gdb": self.tools.toolchain,
            "arm-none-eabi-objcopy": self.tools.toolchain,
            "arm-none-eabi-size": self.tools.toolchain,
        }
        directory = directory_map.get(name, self.tools.toolchain)
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
            "cmake_toolchain_file": str(self.config.cmake_toolchain_file),
        }
