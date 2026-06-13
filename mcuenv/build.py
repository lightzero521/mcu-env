"""CMake + Ninja build helpers."""

from __future__ import annotations

from pathlib import Path

from mcuenv.config import ProjectConfig, load_project_config
from mcuenv.env import EnvManager
from mcuenv.targets import get_target
from mcuenv.util import run_command


def _resolve_generator(project: ProjectConfig, env: EnvManager) -> str:
    return project.generator or env.config.build_generator


def _resolve_cpu(project: ProjectConfig) -> str:
    if not project.target:
        return ""
    return get_target(project.target).cpu


def build_project(
    project_dir: Path | None = None,
    *,
    verbose: bool = False,
    env: EnvManager | None = None,
) -> int:
    manager = env or EnvManager()
    project = load_project_config(project_dir)
    build_dir = project.root / project.build_dir
    generator = _resolve_generator(project, manager)
    cpu = _resolve_cpu(project)

    cmake = manager.tool_binary("cmake")
    env_vars = manager.as_dict()

    configure_args = [
        str(cmake),
        "-S",
        str(project.root),
        "-B",
        str(build_dir),
        "-G",
        generator,
        f"-DCMAKE_TOOLCHAIN_FILE={manager.config.cmake_toolchain_file}",
    ]
    if cpu:
        configure_args.append(f"-DCMAKE_SYSTEM_PROCESSOR={cpu}")

    code = run_command(configure_args, env=env_vars, verbose=verbose)
    if code != 0:
        return code

    build_args = [str(cmake), "--build", str(build_dir)]
    return run_command(build_args, env=env_vars, verbose=verbose)


def clean_project(
    project_dir: Path | None = None,
    *,
    env: EnvManager | None = None,
) -> int:
    manager = env or EnvManager()
    project = load_project_config(project_dir)
    build_dir = project.root / project.build_dir
    cmake = manager.tool_binary("cmake")

    if not build_dir.exists():
        print(f"Build directory not found: {build_dir}")
        return 0

    return run_command(
        [str(cmake), "--build", str(build_dir), "--target", "clean"],
        env=manager.as_dict(),
    )
