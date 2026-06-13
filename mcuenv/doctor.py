"""Environment health checks."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from mcuenv.env import EnvManager
from mcuenv.util import run_command


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def _run_version(env: EnvManager, tool: str, args: list[str]) -> CheckResult:
    try:
        binary = env.tool_binary(tool)
    except FileNotFoundError as exc:
        return CheckResult(name=tool, ok=False, detail=str(exc))

    completed = run_command(
        [str(binary), *args],
        env=env.as_dict(),
    )
    if completed != 0:
        return CheckResult(name=tool, ok=False, detail=f"exit code {completed}")

    return CheckResult(name=tool, ok=True, detail=str(binary))


def run_doctor(env: EnvManager | None = None) -> list[CheckResult]:
    manager = env or EnvManager()
    results: list[CheckResult] = []

    if sys.version_info < (3, 11):
        results.append(
            CheckResult(
                name="python",
                ok=False,
                detail=f"Python 3.11+ required, current is {sys.version.split()[0]}",
            )
        )
    else:
        results.append(
            CheckResult(
                name="python",
                ok=True,
                detail=sys.version.split()[0],
            )
        )

    describe = manager.describe()
    for key in (
        "toolchain_dir",
        "cmake_dir",
        "ninja_dir",
        "openocd_dir",
        "openocd_scripts",
        "cmake_toolchain_file",
    ):
        path = describe[key]
        exists = Path(path).exists()
        results.append(
            CheckResult(
                name=key,
                ok=exists,
                detail=path,
            )
        )

    results.extend(
        [
            _run_version(manager, "arm-none-eabi-gcc", ["--version"]),
            _run_version(manager, "cmake", ["--version"]),
            _run_version(manager, "ninja", ["--version"]),
            _run_version(manager, "openocd", ["--version"]),
        ]
    )
    return results


def print_doctor_report(results: list[CheckResult]) -> int:
    failed = 0
    for result in results:
        status = "OK" if result.ok else "FAIL"
        print(f"[{status}] {result.name}: {result.detail}")
        if not result.ok:
            failed += 1

    if failed:
        print(f"\n{failed} check(s) failed.")
        return 1

    print("\nAll checks passed.")
    return 0
