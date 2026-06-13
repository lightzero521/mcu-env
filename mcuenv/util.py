"""Shared helpers."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Mapping, Sequence


def is_windows() -> bool:
    return platform.system() == "Windows"


def exe_name(name: str) -> str:
    return f"{name}.exe" if is_windows() else name


def which(name: str, paths: Sequence[Path]) -> Path | None:
    candidate_name = exe_name(name)
    for directory in paths:
        candidate = directory / candidate_name
        if candidate.is_file():
            return candidate
    return shutil.which(name, path=os.pathsep.join(str(path) for path in paths))


def run_command(
    command: Sequence[str],
    *,
    env: Mapping[str, str] | None = None,
    cwd: Path | None = None,
    verbose: bool = False,
) -> int:
    if verbose:
        print(f"+ {' '.join(command)}", flush=True)

    completed = subprocess.run(
        list(command),
        env=dict(env) if env is not None else None,
        cwd=str(cwd) if cwd is not None else None,
        check=False,
    )
    return completed.returncode


def require_python_version(min_major: int = 3, min_minor: int = 11) -> None:
    if sys.version_info < (min_major, min_minor):
        raise SystemExit(
            f"mcuenv requires Python {min_major}.{min_minor}+ "
            f"(current: {sys.version.split()[0]})"
        )
