"""Map CPU profiles to CMake toolchain files."""

from __future__ import annotations

from pathlib import Path

from mcuenv.env import EnvManager

CPU_TOOLCHAIN_FILES: dict[str, str] = {
    "cortex-m0": "cmake/toolchain-cortex-m0.cmake",
    "cortex-m0plus": "cmake/toolchain-cortex-m0plus.cmake",
    "cortex-m0+": "cmake/toolchain-cortex-m0plus.cmake",
    "cortex-m3": "cmake/toolchain-cortex-m3.cmake",
    "cortex-m4": "cmake/toolchain-cortex-m4.cmake",
    "cortex-m7": "cmake/toolchain-cortex-m7.cmake",
    "cortex-m33": "cmake/toolchain-cortex-m33.cmake",
}


def resolve_toolchain_file(env: EnvManager, cpu: str) -> Path:
    cpu_key = cpu.strip().lower()
    relative = CPU_TOOLCHAIN_FILES.get(cpu_key)
    if relative:
        candidate = env.root / relative
        if candidate.is_file():
            return candidate

    fallback = env.config.cmake_toolchain_file
    if fallback.is_file():
        return fallback

    if relative:
        raise FileNotFoundError(f"Toolchain file not found: {env.root / relative}")

    known = ", ".join(sorted(CPU_TOOLCHAIN_FILES))
    raise KeyError(
        f"Unknown CPU profile '{cpu}'. Known profiles: {known}. "
        "Set [toolchain].cmake_toolchain_file in mcuenv.toml as fallback."
    )


def resolve_toolchain_for_build(
    env: EnvManager,
    project_root: Path,
    toolchain_file: str,
    cpu: str,
) -> Path:
    if toolchain_file.strip():
        path = Path(toolchain_file)
        if not path.is_absolute():
            path = project_root / path
        if not path.is_file():
            raise FileNotFoundError(
                f"Project toolchain file not found: {path}. "
                "Check [build].toolchain_file in mcuenv.project.toml."
            )
        return path.resolve()

    if cpu:
        return resolve_toolchain_file(env, cpu)

    fallback = env.config.cmake_toolchain_file
    if fallback.is_file():
        return fallback

    raise FileNotFoundError(
        "No toolchain file configured. Set [build].toolchain_file in "
        "mcuenv.project.toml, set [project].target, or configure "
        "[toolchain].cmake_toolchain_file in mcuenv.toml."
    )
