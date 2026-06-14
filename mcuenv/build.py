"""CMake + Ninja build helpers."""

from __future__ import annotations

import sys
from pathlib import Path

from mcuenv.config import ProjectConfig, load_project_config
from mcuenv.env import EnvManager
from mcuenv.registry_db import resolve_registry_paths
from mcuenv.targets import get_target
from mcuenv.toolchain_cmake import resolve_toolchain_for_build
from mcuenv.util import is_windows, run_command


def _registry_paths(env: EnvManager):
    return resolve_registry_paths(env.root, env.config.registry_database)


def _resolve_generator(project: ProjectConfig, env: EnvManager) -> str:
    return project.generator or env.config.build_generator


def _resolve_cpu(project: ProjectConfig, env: EnvManager) -> str:
    if not project.target:
        return ""
    return get_target(project.target, paths=_registry_paths(env)).cpu


def _run_project_script(
    project: ProjectConfig,
    script_path: str,
    *,
    verbose: bool,
) -> int:
    script = Path(script_path)
    if not script.is_absolute():
        script = project.root / script
    if not script.is_file():
        raise FileNotFoundError(f"Build script not found: {script}")

    if script.suffix.lower() == ".py":
        command = [sys.executable, str(script)]
    elif script.suffix.lower() == ".ps1" and is_windows():
        command = ["powershell", "-File", str(script)]
    else:
        command = [str(script)]

    return run_command(command, verbose=verbose, cwd=project.root)


def build_project(
    project_dir: Path | None = None,
    *,
    verbose: bool = False,
    env: EnvManager | None = None,
) -> int:
    manager = env or EnvManager()
    activation_error = EnvManager.require_active_shell(require_cross_compiler=True)
    if activation_error:
        print(activation_error, file=sys.stderr)
        return 1

    project = load_project_config(project_dir)
    build_dir = project.root / project.build_dir
    generator = _resolve_generator(project, manager)
    cpu = _resolve_cpu(project, manager)
    toolchain_file = resolve_toolchain_for_build(
        manager,
        project.root,
        project.toolchain_file,
        cpu,
    )

    cmake = manager.tool_binary("cmake")

    for script in project.pre_build:
        code = _run_project_script(project, script, verbose=verbose)
        if code != 0:
            return code

    if verbose:
        print(f"Toolchain: {toolchain_file}" + (f" (cpu={cpu})" if cpu else ""), flush=True)

    configure_args = [
        str(cmake),
        "-S",
        str(project.root),
        "-B",
        str(build_dir),
        "-G",
        generator,
        f"-DCMAKE_TOOLCHAIN_FILE={toolchain_file}",
    ]
    if project.linker_script:
        linker = Path(project.linker_script)
        if not linker.is_absolute():
            linker = project.root / linker
        configure_args.append(f"-DCMAKE_EXE_LINKER_FLAGS=-T{linker.as_posix()}")

    code = run_command(configure_args, verbose=verbose)
    if code != 0:
        return code

    build_args = [str(cmake), "--build", str(build_dir)]
    code = run_command(build_args, verbose=verbose)
    if code != 0:
        return code

    for script in project.post_build:
        code = _run_project_script(project, script, verbose=verbose)
        if code != 0:
            return code

    return 0


def clean_project(
    project_dir: Path | None = None,
    *,
    env: EnvManager | None = None,
) -> int:
    manager = env or EnvManager()
    activation_error = EnvManager.require_active_shell(require_cross_compiler=True)
    if activation_error:
        print(activation_error, file=sys.stderr)
        return 1

    project = load_project_config(project_dir)
    build_dir = project.root / project.build_dir
    cmake = manager.tool_binary("cmake")

    if not build_dir.exists():
        print(f"Build directory not found: {build_dir}")
        return 0

    return run_command([str(cmake), "--build", str(build_dir), "--target", "clean"])
