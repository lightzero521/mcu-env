"""Shared helpers."""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Mapping, Sequence


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


def format_elapsed(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.2f}s"
    minutes = int(seconds // 60)
    remainder = seconds - minutes * 60
    return f"{minutes}m {remainder:.1f}s"


class CommandTimer:
    """Print elapsed time when a command finishes."""

    def __init__(self, label: str) -> None:
        self.label = label
        self._start = 0.0

    def __enter__(self) -> CommandTimer:
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args: object) -> None:
        elapsed = time.perf_counter() - self._start
        print(f"{self.label} finished in {format_elapsed(elapsed)}", flush=True)


class _ProgressTracker:
    _NINJA_PROGRESS_RE = re.compile(r"^\s*\[\d+/\d+\]")
    _FRACTION_RE = re.compile(r"\[(\d+)/(\d+)\]")

    def __init__(self) -> None:
        self._last_pct = -1
        self._line_open = False

    def is_progress_line(self, line: str) -> bool:
        return bool(self._NINJA_PROGRESS_RE.match(line))

    def feed(self, line: str) -> None:
        match = self._FRACTION_RE.search(line)
        if not match:
            return
        current = int(match.group(1))
        total = int(match.group(2))
        if total <= 0:
            return
        pct = min(100, int(current * 100 / total))
        if pct == self._last_pct:
            return
        self._last_pct = pct
        width = 40
        filled = int(width * pct / 100)
        bar = "#" * filled + "-" * (width - filled)
        sys.stdout.write(f"\r[{bar}] {pct:3d}%")
        sys.stdout.flush()
        self._line_open = True

    def end_line(self) -> None:
        if not self._line_open:
            return
        sys.stdout.write("\n")
        sys.stdout.flush()
        self._line_open = False

    def finish(self) -> None:
        if not self._line_open:
            return
        if self._last_pct < 100:
            width = 40
            bar = "#" * width
            sys.stdout.write(f"\r[{bar}] 100%")
            sys.stdout.flush()
        sys.stdout.write("\n")
        sys.stdout.flush()
        self._line_open = False


def make_project_path_rewriter(project_root: Path) -> Callable[[str], str]:
    """Shorten absolute paths under project_root to project-relative form."""

    root = project_root.resolve()
    posix_root = root.as_posix().rstrip("/")
    prefixes: list[str] = []

    if posix_root:
        prefixes.append(posix_root + "/")

    native = str(root)
    if native:
        if not native.endswith((os.sep, "/")):
            prefixes.append(native + os.sep)
        else:
            prefixes.append(native)

    if is_windows() and root.drive:
        drive = root.drive[0]
        rest = posix_root.split(":", 1)[-1].lstrip("/")
        if rest:
            prefixes.append(f"{drive.upper()}_/{rest}/")
            prefixes.append(f"{drive.lower()}_/{rest}/")

    seen: set[str] = set()
    ordered_prefixes: list[str] = []
    for prefix in sorted(prefixes, key=len, reverse=True):
        if prefix not in seen:
            seen.add(prefix)
            ordered_prefixes.append(prefix)

    exact_paths: list[str] = []
    if posix_root:
        exact_paths.append(posix_root)
    if native:
        exact_paths.append(native.rstrip(os.sep))
    if is_windows() and root.drive:
        rest = posix_root.split(":", 1)[-1].lstrip("/")
        if rest:
            exact_paths.append(f"{root.drive[0].upper()}_/{rest}")
            exact_paths.append(f"{root.drive[0].lower()}_/{rest}")
    ordered_exact = sorted(set(exact_paths), key=len, reverse=True)

    flags = re.IGNORECASE if is_windows() else 0

    def rewrite(line: str) -> str:
        result = line
        for prefix in ordered_prefixes:
            result = re.sub(re.escape(prefix), "", result, flags=flags)
        for path in ordered_exact:
            result = re.sub(
                re.escape(path) + r"(?![/\\])",
                ".",
                result,
                flags=flags,
            )
        return result

    return rewrite


_NINJA_BUILDING_RE = re.compile(r"^\[\d+/\d+\]\s+Building\b", re.IGNORECASE)
_NINJA_STEP_RE = re.compile(r"^\[\d+/\d+\]")
_SOURCE_EXT = r"(?:cpp|cxx|cc|c|s|S)"
_SOURCE_IN_OBJ_RE = re.compile(
    rf"\.dir[\\/](?:.*[\\/])?([^\\/]+\.{_SOURCE_EXT})\.(?:c\.)?obj\b",
    re.IGNORECASE,
)
_COMPILE_SOURCE_RE = re.compile(
    rf'-c\s+(?:"([^"]+\.{_SOURCE_EXT})"|([^\s]+\.{_SOURCE_EXT}))',
    re.IGNORECASE,
)
_TOOL_COMMAND_RE = re.compile(
    r"(?:^|[\\/\s])(?:arm-none-eabi-)?(?:gcc|g\+\+|clang|ld|as)(?:\.exe)?\b",
    re.IGNORECASE,
)


def _contains_tool_command(line: str) -> bool:
    return bool(_TOOL_COMMAND_RE.search(line))


def _source_name_from_compile_command(line: str) -> str | None:
    match = _COMPILE_SOURCE_RE.search(line)
    if not match:
        return None
    source = match.group(1) or match.group(2)
    return Path(source).name


def _is_verbose_tool_command_line(line: str) -> bool:
    stripped = line.lstrip()
    if not stripped:
        return False
    if stripped.startswith("cd ") and "&&" in stripped:
        return True
    return _contains_tool_command(stripped)


def make_verbose_build_output_filter(project_root: Path) -> Callable[[str], str | None]:
    """In verbose build mode, show Keil-style compile lines and hide tool commands."""

    shorten = make_project_path_rewriter(project_root)

    def transform(line: str) -> str | None:
        text = line.rstrip("\r\n")
        if not text.strip():
            return None

        if _NINJA_BUILDING_RE.match(text):
            match = _SOURCE_IN_OBJ_RE.search(text)
            if match:
                return f"compiling {match.group(1)}\n"
            return None

        if _NINJA_STEP_RE.match(text):
            if _contains_tool_command(text):
                source_name = _source_name_from_compile_command(text)
                if source_name:
                    return f"compiling {source_name}\n"
                if re.search(r"\b-o\b", text) and re.search(
                    r"\.elf\b", text, re.IGNORECASE
                ):
                    return "linking\n"
                return None
            return shorten(line)

        if _is_verbose_tool_command_line(text):
            source_name = _source_name_from_compile_command(text)
            if source_name:
                return f"compiling {source_name}\n"
            return None

        return shorten(line)

    return transform


class FlashProgressBar:
    """Console progress bar driven by J-Link DLL flash callbacks."""

    def __init__(self) -> None:
        self._last_pct = -1
        self._prefix = ""

    def update(self, action: str, progress_string: str, percentage: int) -> None:
        if action.lower() == "compare":
            return

        pct = max(0, min(100, int(percentage)))
        prefix = action or progress_string or "Flash"
        if prefix != self._prefix or pct != self._last_pct:
            self._prefix = prefix
            self._last_pct = pct
            width = 40
            filled = int(width * pct / 100)
            bar = "#" * filled + "-" * (width - filled)
            sys.stdout.write(f"\r[{prefix}] [{bar}] {pct:3d}%")
            sys.stdout.flush()

    def finish(self) -> None:
        if self._last_pct >= 0:
            sys.stdout.write("\n")
            sys.stdout.flush()


def run_command(
    command: Sequence[str],
    *,
    env: Mapping[str, str] | None = None,
    cwd: Path | None = None,
    verbose: bool = False,
    progress: bool = False,
    transform_line: Callable[[str], str | None] | None = None,
) -> int:
    if progress or verbose or transform_line is not None:
        return run_command_stream(
            command,
            env=env,
            cwd=cwd,
            verbose=verbose,
            progress=progress,
            transform_line=transform_line,
        )

    completed = subprocess.run(
        list(command),
        env=dict(env) if env is not None else None,
        cwd=str(cwd) if cwd is not None else None,
        check=False,
    )
    return completed.returncode


def run_command_stream(
    command: Sequence[str],
    *,
    env: Mapping[str, str] | None = None,
    cwd: Path | None = None,
    verbose: bool = False,
    progress: bool = False,
    transform_line: Callable[[str], str | None] | None = None,
) -> int:
    if verbose:
        print(f"+ {' '.join(command)}", flush=True)

    tracker = _ProgressTracker() if progress else None
    process = subprocess.Popen(
        list(command),
        env=dict(env) if env is not None else None,
        cwd=str(cwd) if cwd is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    assert process.stdout is not None
    for line in process.stdout:
        if transform_line is not None:
            line = transform_line(line)
            if line is None:
                continue
        if tracker is not None:
            tracker.feed(line)
            if verbose or not tracker.is_progress_line(line):
                tracker.end_line()
                sys.stdout.write(line)
        elif verbose:
            sys.stdout.write(line)

    if tracker is not None:
        tracker.finish()

    return process.wait()


def require_python_version(min_major: int = 3, min_minor: int = 11) -> None:
    if sys.version_info < (min_major, min_minor):
        raise SystemExit(
            f"mcuenv requires Python {min_major}.{min_minor}+ "
            f"(current: {sys.version.split()[0]})"
        )
