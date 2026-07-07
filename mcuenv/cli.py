"""Command-line interface for mcuenv."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mcuenv import __version__
from mcuenv.build import build_project, clean_project, fullclean_project
from mcuenv.config import apply_target_defaults, default_flash_image, find_project_root, load_project_config, write_project_config
from mcuenv.doctor import print_doctor_report, run_doctor
from mcuenv.erase import erase_project
from mcuenv.env import EnvManager
from mcuenv.flash import describe_flash_settings, flash_project
from mcuenv.prompt import format_prompt_bash, format_prompt_segment
from mcuenv.registry_db import (
    export_to_toml,
    init_registry,
    resolve_registry_paths,
    sync_resource_status,
)
from mcuenv.shell import deactivate_lines
from mcuenv.shell_init import run_shell_init
from mcuenv.targets import get_target, list_targets
from mcuenv.util import is_windows, require_python_version
from mcuenv.web_app import run_web_server


def _default_export_format() -> str:
    return "ps1" if is_windows() else "bash"


def _registry_paths(env: EnvManager):
    return resolve_registry_paths(env.root, env.config.registry_database)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mcuenv.py",
        description="MCU development environment manager",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Override MCUENV_ROOT",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print commands and enable verbose tool output (e.g. cmake --build --verbose)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("doctor", help="Verify bundled tools and paths")
    subparsers.add_parser("env-info", help="Show resolved environment paths")

    export_parser = subparsers.add_parser(
        "export",
        help="Print shell commands to activate the environment",
    )
    export_parser.add_argument(
        "--format",
        choices=["ps1", "powershell", "bash", "sh"],
        default=_default_export_format(),
        help="Shell export format",
    )

    deactivate_parser = subparsers.add_parser(
        "deactivate",
        help="Print shell commands to leave the activated environment",
    )
    deactivate_parser.add_argument(
        "--format",
        choices=["ps1", "powershell", "bash", "sh"],
        default=_default_export_format(),
        help="Shell deactivate format",
    )

    prompt_segment_parser = subparsers.add_parser(
        "prompt-segment",
        help="Print the colored prompt prefix for the current shell",
    )
    prompt_segment_parser.add_argument(
        "--format",
        choices=["ps1", "powershell", "bash", "sh"],
        default=_default_export_format(),
        help="Shell prompt format",
    )

    list_targets_parser = subparsers.add_parser(
        "list-targets",
        help="List supported STM32/GD32 target presets",
    )
    list_targets_parser.add_argument(
        "--family",
        choices=["stm32", "gd32"],
        default=None,
        help="Filter by MCU family",
    )

    set_target_parser = subparsers.add_parser(
        "set-target",
        help="Set the active target for the current project",
    )
    set_target_parser.add_argument("target", help="Target preset name")
    set_target_parser.add_argument(
        "--project-dir",
        type=Path,
        default=None,
        help="Project directory (default: auto-detect)",
    )
    set_target_parser.add_argument(
        "--name",
        default=None,
        help="Project name written to mcuenv.project.toml",
    )

    build_parser = subparsers.add_parser("build", help="Configure and build the project")
    build_parser.add_argument(
        "--project-dir",
        type=Path,
        default=None,
        help="Project directory (default: auto-detect)",
    )
    build_mode = build_parser.add_mutually_exclusive_group()
    build_mode.add_argument(
        "--debug",
        action="store_true",
        help="Build with CMAKE_BUILD_TYPE=Debug (overrides [build].build_type)",
    )
    build_mode.add_argument(
        "--release",
        action="store_true",
        help="Build with CMAKE_BUILD_TYPE=Release (overrides [build].build_type)",
    )

    clean_parser = subparsers.add_parser(
        "clean",
        help="Remove build artifacts (keeps CMake cache in build/)",
    )
    clean_parser.add_argument(
        "--project-dir",
        type=Path,
        default=None,
        help="Project directory (default: auto-detect)",
    )

    fullclean_parser = subparsers.add_parser(
        "fullclean",
        help="Delete entire build directory (CMake reconfigures on next build)",
    )
    fullclean_parser.add_argument(
        "--project-dir",
        type=Path,
        default=None,
        help="Project directory (default: auto-detect)",
    )

    flash_parser = subparsers.add_parser("flash", help="Flash firmware via configured backend")
    flash_parser.add_argument(
        "--project-dir",
        type=Path,
        default=None,
        help="Project directory (default: auto-detect)",
    )
    flash_parser.add_argument(
        "--interface",
        default=None,
        help="OpenOCD adapter config name (without .cfg), overrides [flash.openocd].adapter",
    )
    flash_parser.add_argument(
        "--target",
        dest="openocd_target",
        default=None,
        help="OpenOCD target config name, without .cfg",
    )
    flash_parser.add_argument(
        "--elf",
        type=Path,
        default=None,
        help="Firmware ELF path override",
    )

    erase_parser = subparsers.add_parser(
        "erase",
        help="Erase chip flash (pyOCD or J-Link backend)",
    )
    erase_parser.add_argument(
        "--project-dir",
        type=Path,
        default=None,
        help="Project directory (default: auto-detect)",
    )

    shell_parser = subparsers.add_parser(
        "shell",
        help="Shell integration helpers",
    )
    shell_subparsers = shell_parser.add_subparsers(dest="shell_command", required=True)

    shell_init_parser = shell_subparsers.add_parser(
        "init",
        help="Generate or install mcuenv-on shell helper",
    )
    shell_init_parser.add_argument(
        "--format",
        choices=["ps1", "powershell", "bash", "sh", "all"],
        default="all" if not is_windows() else "ps1",
        help="Shell profile format to generate or install",
    )
    shell_init_parser.add_argument(
        "--install",
        action="store_true",
        help="Write helpers into the user's shell profile",
    )

    registry_parser = subparsers.add_parser(
        "registry",
        help="Manage chip/SDK/manual registry",
    )
    registry_subparsers = registry_parser.add_subparsers(
        dest="registry_command",
        required=True,
    )
    registry_subparsers.add_parser(
        "init",
        help="Initialize SQLite database and seed default chips",
    )
    registry_subparsers.add_parser(
        "export",
        help="Export packages/manuals registry to registry/*.toml",
    )
    registry_subparsers.add_parser(
        "sync-status",
        help="Scan packages/manuals paths and update installed/missing status",
    )

    web_parser = subparsers.add_parser(
        "web",
        help="Run registry web backend",
    )
    web_subparsers = web_parser.add_subparsers(dest="web_command", required=True)
    web_serve_parser = web_subparsers.add_parser(
        "serve",
        help="Start SQLite-backed registry admin web server",
    )
    web_serve_parser.add_argument("--host", default="127.0.0.1")
    web_serve_parser.add_argument("--port", type=int, default=7654)

    return parser


def _print_env_info(env: EnvManager) -> int:
    print(f"mcuenv {__version__}")
    for key, value in env.describe().items():
        print(f"{key}: {value}")
    return 0


def _print_targets(env: EnvManager, family: str | None) -> int:
    paths = _registry_paths(env)
    for preset in list_targets(family, paths=paths):
        note = f" ({preset.note})" if preset.note else ""
        print(
            f"{preset.name:18} {preset.family:5} {preset.mcu:16} "
            f"{preset.cpu:12} {preset.tool:7} probe={preset.probe}{note}"
        )
    return 0


def _cmd_set_target(args: argparse.Namespace, env: EnvManager) -> int:
    paths = _registry_paths(env)
    preset = get_target(args.target, paths=paths)
    project_root = find_project_root(args.project_dir)
    project = load_project_config(project_root)
    project.root = project_root
    apply_target_defaults(project, preset)
    if args.name:
        project.name = args.name
    elif project.name == "firmware" and (project_root / "CMakeLists.txt").is_file():
        project.name = project_root.name

    project.flash_image = default_flash_image(project)

    write_project_config(project)
    print(f"Target set to {preset.name} ({preset.mcu})")
    print(f"Wrote {project_root / 'mcuenv.project.toml'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    require_python_version()
    parser = _build_parser()
    args = parser.parse_args(argv)
    env = EnvManager(args.root)

    if args.command == "doctor":
        return print_doctor_report(run_doctor(env))

    if args.command == "env-info":
        return _print_env_info(env)

    if args.command == "export":
        for line in env.export_lines(args.format):
            print(line)
        return 0

    if args.command == "deactivate":
        for line in deactivate_lines(args.format):
            print(line)
        return 0

    if args.command == "prompt-segment":
        if args.format in {"bash", "sh"}:
            sys.stdout.write(format_prompt_bash())
        else:
            sys.stdout.write(format_prompt_segment())
        return 0

    if args.command == "list-targets":
        return _print_targets(env, args.family)

    if args.command == "set-target":
        return _cmd_set_target(args, env)

    if args.command == "build":
        try:
            return build_project(
                args.project_dir,
                verbose=args.verbose,
                debug=args.debug,
                release=args.release,
                env=env,
            )
        except ValueError as exc:
            print(exc, file=sys.stderr)
            return 1

    if args.command == "clean":
        return clean_project(args.project_dir, verbose=args.verbose, env=env)

    if args.command == "fullclean":
        return fullclean_project(args.project_dir, env=env)

    if args.command == "flash":
        try:
            return flash_project(
                args.project_dir,
                interface=args.interface,
                target=args.openocd_target,
                elf=args.elf,
                verbose=args.verbose,
                env=env,
            )
        except (FileNotFoundError, ValueError) as exc:
            print(exc, file=sys.stderr)
            return 1

    if args.command == "erase":
        try:
            return erase_project(
                args.project_dir,
                verbose=args.verbose,
                env=env,
            )
        except (FileNotFoundError, ValueError) as exc:
            print(exc, file=sys.stderr)
            return 1

    if args.command == "shell":
        if args.shell_command == "init":
            return run_shell_init(
                env.root,
                fmt=args.format,
                install=args.install,
            )
        parser.error(f"Unknown shell command: {args.shell_command}")
        return 2

    if args.command == "registry":
        paths = _registry_paths(env)
        if args.registry_command == "init":
            init_registry(paths, force=True)
            print(f"Registry database: {paths.database}")
            print("Seeded default chips and imported packages/manuals TOML if present.")
            return 0
        if args.registry_command == "export":
            export_to_toml(paths)
            print(f"Exported SQLite registry to {paths.registry_dir}")
            return 0
        if args.registry_command == "sync-status":
            counts = sync_resource_status(paths)
            print(f"Updated package rows: {counts['packages']}")
            print(f"Updated manual rows: {counts['manuals']}")
            return 0
        parser.error(f"Unknown registry command: {args.registry_command}")
        return 2

    if args.command == "web":
        if args.web_command == "serve":
            run_web_server(_registry_paths(env), host=args.host, port=args.port)
            return 0
        parser.error(f"Unknown web command: {args.web_command}")
        return 2

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
