"""Target presets loaded from the SQLite chip registry."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mcuenv.config import detect_root, load_global_config
from mcuenv.registry_db import RegistryPaths, get_chip, list_chips, resolve_registry_paths


@dataclass(frozen=True)
class TargetPreset:
    name: str
    family: str
    mcu: str
    series: str
    cpu: str
    probe: str
    backend: str
    jlink_device: str
    openocd_interface: str
    openocd_target: str
    pyocd_target: str
    note: str = ""


def _registry_paths(root: Path | None = None) -> RegistryPaths:
    env_root = detect_root(root)
    config = load_global_config(env_root)
    return resolve_registry_paths(env_root, config.registry_database)


def _chip_to_preset(chip: dict) -> TargetPreset:
    return TargetPreset(
        name=chip["id"],
        family=chip["family"],
        mcu=chip["mcu"],
        series=chip.get("series", ""),
        cpu=chip.get("cpu", ""),
        probe=chip.get("probe", "stlink"),
        backend=chip.get("backend", "openocd"),
        jlink_device=chip.get("jlink_device", ""),
        openocd_interface=chip.get("openocd_interface", "stlink"),
        openocd_target=chip.get("openocd_target", ""),
        pyocd_target=chip.get("pyocd_target", ""),
        note=chip.get("note", ""),
    )


def get_target(
    name: str,
    *,
    paths: RegistryPaths | None = None,
    root: Path | None = None,
) -> TargetPreset:
    registry = paths or _registry_paths(root)
    chip = get_chip(registry, name)
    if chip is None:
        known = ", ".join(preset.name for preset in list_targets(paths=registry))
        raise KeyError(f"Unknown target '{name}'. Known targets: {known}")
    return _chip_to_preset(chip)


def list_targets(
    family: str | None = None,
    *,
    paths: RegistryPaths | None = None,
    root: Path | None = None,
) -> list[TargetPreset]:
    registry = paths or _registry_paths(root)
    return [_chip_to_preset(chip) for chip in list_chips(registry, family=family)]
