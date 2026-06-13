"""Command-line interface for mcuenv."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mcuenv import __version__
from mcuenv.build import build_project, clean_project
from mcuenv.config import find_project_root, load_project_config, write_project_config
from mcuenv.doctor import print_doctor_report, run_doctor
from mcuenv.env import EnvManager
from mcuenv.flash import describe_flash_settings, flash_project
from mcuenv.targets import get_target, list_targets
from mcuenv.util import is_windows, require_python_version


def _default_export_format() -> str:
    return "ps1" if is_windows() else "bash"


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
        help="Print commands before execution",
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

    clean_parser = subparsers.add_parser("clean", help="Clean the project build directory")
    clean_parser.add_argument(
        "--project-dir",
        type=Path,
        default=None,
        help="Project directory (default: auto-detect)",
    )

    flash_parser = subparsers.add_parser("flash", help="Flash firmware with OpenOCD")
    flash_parser.add_argument(
        "--project-dir",
        type=Path,
        default=None,
        help="Project directory (default: auto-detect)",
    )
    flash_parser.add_argument(
        "--interface",
        default=None,
        help="OpenOCD interface config name, without .cfg",
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

    return parser


def _print_env_info(env: EnvManager) -> int:
    print(f"mcuenv {__version__}")
    for key, value in env.describe().items():
        print(f"{key}: {value}")
    return 0


def _print_targets(family: str | None) -> int:
    for preset in list_targets(family):
        note = f" ({preset.note})" if preset.note else ""
        print(
            f"{preset.name:16} {preset.family:5} {preset.mcu:12} "
            f"{preset.cpu:12} openocd={preset.openocd_target}{note}"
        )
    return 0


def _cmd_set_target(args: argparse.Namespace, env: EnvManager) -> int:
    preset = get_target(args.target)
    project_root = find_project_root(args.project_dir)
    project = load_project_config(project_root)
    project.root = project_root
    project.target = preset.name
    project.openocd_target = preset.openocd_target
    project.openocd_interface = preset.openocd_interface
    if args.name:
        project.name = args.name
    elif project.name == "firmware" and (project_root / "CMakeLists.txt").is_file():
        project.name = project_root.name

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

    if args.command == "list-targets":
        return _print_targets(args.family)

    if args.command == "set-target":
        return _cmd_set_target(args, env)

    if args.command == "build":
        return build_project(args.project_dir, verbose=args.verbose, env=env)

    if args.command == "clean":
        return clean_project(args.project_dir, env=env)

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

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
