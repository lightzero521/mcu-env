"""Environment health checks."""

from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from mcuenv.env import EnvManager
from mcuenv.registry_db import list_chips, resolve_registry_paths
from mcuenv.util import run_command


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def _run_version(tool: str, args: list[str]) -> CheckResult:
    binary = shutil.which(tool)
    if binary is None:
        return CheckResult(
            name=tool,
            ok=False,
            detail=f"{tool} not found on PATH (run mcuenv-on first)",
        )

    completed = run_command([binary, *args])
    if completed != 0:
        return CheckResult(name=tool, ok=False, detail=f"exit code {completed}")

    return CheckResult(name=tool, ok=True, detail=binary)


def _check_registry(env: EnvManager) -> CheckResult:
    paths = resolve_registry_paths(env.root, env.config.registry_database)
    if not paths.database.is_file():
        return CheckResult(
            name="registry.db",
            ok=False,
            detail=f"Missing {paths.database}. Run: mcuenv.py registry init",
        )

    try:
        chips = list_chips(paths)
    except Exception as exc:
        return CheckResult(name="registry.db", ok=False, detail=str(exc))

    if not chips:
        return CheckResult(
            name="registry.db",
            ok=False,
            detail=f"No chips in {paths.database}. Run: mcuenv.py registry init",
        )

    return CheckResult(
        name="registry.db",
        ok=True,
        detail=f"{paths.database} ({len(chips)} chip(s))",
    )


def run_doctor(env: EnvManager | None = None) -> list[CheckResult]:
    manager = env or EnvManager()
    results: list[CheckResult] = []

    activation_error = EnvManager.require_active_shell()
    if activation_error:
        results.append(CheckResult(name="mcuenv", ok=False, detail=activation_error))
        return results

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

    results.append(_check_registry(manager))

    describe = manager.describe()
    for key in (
        "toolchain_dir",
        "cmake_dir",
        "ninja_dir",
        "openocd_dir",
        "openocd_scripts",
        "pyocd_dir",
        "cmake_toolchain_file",
    ):
        path = describe[key]
        if path == "(not configured)":
            continue
        exists = Path(path).exists()
        results.append(
            CheckResult(
                name=key,
                ok=exists,
                detail=path,
            )
        )

    tool_checks = [
        _run_version("arm-none-eabi-gcc", ["--version"]),
        _run_version("cmake", ["--version"]),
        _run_version("ninja", ["--version"]),
        _run_version("openocd", ["--version"]),
    ]
    if manager.tools.pyocd is not None:
        tool_checks.append(_run_version("pyocd", ["--version"]))
    results.extend(tool_checks)
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
