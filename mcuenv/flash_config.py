"""Flash configuration models and resolution."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcuenv.config import GlobalConfig, ProjectConfig
    from mcuenv.targets import TargetPreset


@dataclass(frozen=True)
class FlashJlinkConfig:
    device: str
    interface: str
    speed_khz: int
    serial: str
    ip: str
    reset_strategy: str
    script: str


@dataclass(frozen=True)
class FlashOpenocdConfig:
    adapter: str
    target: str
    transport: str
    adapter_speed_khz: int
    extra_commands: str


@dataclass(frozen=True)
class FlashPyocdConfig:
    target: str
    probe_uid: str
    frequency_hz: int
    connect_mode: str
    pack: str


@dataclass(frozen=True)
class FlashSettings:
    tool: str
    probe: str
    after_program: str
    image: str
    jlink: FlashJlinkConfig
    openocd: FlashOpenocdConfig
    pyocd: FlashPyocdConfig


def default_jlink_config() -> FlashJlinkConfig:
    return FlashJlinkConfig(
        device="",
        interface="swd",
        speed_khz=4000,
        serial="",
        ip="",
        reset_strategy="",
        script="",
    )


def default_openocd_config() -> FlashOpenocdConfig:
    return FlashOpenocdConfig(
        adapter="stlink",
        target="",
        transport="swd",
        adapter_speed_khz=0,
        extra_commands="",
    )


def default_pyocd_config() -> FlashPyocdConfig:
    return FlashPyocdConfig(
        target="",
        probe_uid="",
        frequency_hz=4_000_000,
        connect_mode="halt",
        pack="",
    )


def jlink_config_from_mapping(data: dict[str, Any] | None) -> FlashJlinkConfig:
    section = data or {}
    return FlashJlinkConfig(
        device=str(section.get("device", "")),
        interface=str(section.get("interface", "swd")).lower(),
        speed_khz=int(section.get("speed_khz", 4000) or 4000),
        serial=str(section.get("serial", "")),
        ip=str(section.get("ip", "")).strip(),
        reset_strategy=str(section.get("reset_strategy", "")),
        script=str(section.get("script", "")),
    )


def openocd_config_from_mapping(data: dict[str, Any] | None) -> FlashOpenocdConfig:
    section = data or {}
    return FlashOpenocdConfig(
        adapter=str(section.get("adapter", "stlink")),
        target=str(section.get("target", "")),
        transport=str(section.get("transport", "swd")).lower(),
        adapter_speed_khz=int(section.get("adapter_speed_khz", 0) or 0),
        extra_commands=str(section.get("extra_commands", "")),
    )


def pyocd_config_from_mapping(data: dict[str, Any] | None) -> FlashPyocdConfig:
    section = data or {}
    return FlashPyocdConfig(
        target=str(section.get("target", "")),
        probe_uid=str(section.get("probe_uid", "")),
        frequency_hz=int(section.get("frequency_hz", 4_000_000) or 4_000_000),
        connect_mode=str(section.get("connect_mode", "halt")),
        pack=str(section.get("pack", "")),
    )


def jlink_config_from_preset(preset: TargetPreset) -> FlashJlinkConfig:
    return FlashJlinkConfig(
        device=preset.jlink_device,
        interface="swd",
        speed_khz=4000,
        serial="",
        ip="",
        reset_strategy="",
        script="",
    )


def openocd_config_from_preset(preset: TargetPreset) -> FlashOpenocdConfig:
    return FlashOpenocdConfig(
        adapter=preset.openocd_interface or preset.probe,
        target=preset.openocd_target,
        transport="swd",
        adapter_speed_khz=0,
        extra_commands="",
    )


def pyocd_config_from_preset(preset: TargetPreset) -> FlashPyocdConfig:
    return FlashPyocdConfig(
        target=preset.pyocd_target,
        probe_uid="",
        frequency_hz=4_000_000,
        connect_mode="halt",
        pack="",
    )


def _merge_jlink(project: FlashJlinkConfig, preset: FlashJlinkConfig | None) -> FlashJlinkConfig:
    if preset is None:
        return project
    return FlashJlinkConfig(
        device=project.device or preset.device,
        interface=project.interface or preset.interface,
        speed_khz=project.speed_khz if project.speed_khz else preset.speed_khz,
        serial=project.serial or preset.serial,
        ip=project.ip or preset.ip,
        reset_strategy=project.reset_strategy or preset.reset_strategy,
        script=project.script or preset.script,
    )


def _merge_openocd(
    project: FlashOpenocdConfig,
    preset: FlashOpenocdConfig | None,
) -> FlashOpenocdConfig:
    if preset is None:
        return project
    return FlashOpenocdConfig(
        adapter=project.adapter or preset.adapter,
        target=project.target or preset.target,
        transport=project.transport or preset.transport,
        adapter_speed_khz=project.adapter_speed_khz,
        extra_commands=project.extra_commands or preset.extra_commands,
    )


def _merge_pyocd(project: FlashPyocdConfig, preset: FlashPyocdConfig | None) -> FlashPyocdConfig:
    if preset is None:
        return project
    return FlashPyocdConfig(
        target=project.target or preset.target,
        probe_uid=project.probe_uid or preset.probe_uid,
        frequency_hz=project.frequency_hz if project.frequency_hz else preset.frequency_hz,
        connect_mode=project.connect_mode or preset.connect_mode,
        pack=project.pack or preset.pack,
    )


def _validate_probe_tool(tool: str, probe: str) -> None:
    if tool == "jlink" and probe != "jlink":
        raise ValueError(
            f"[flash] tool is 'jlink' but probe is '{probe}'. Set probe = \"jlink\"."
        )
    if tool == "pyocd" and probe not in {"stlink", "cmsis-dap", "jlink"}:
        raise ValueError(
            f"[flash] pyocd probe '{probe}' is not supported. Use stlink, cmsis-dap, or jlink."
        )


def _validate_active_tool(settings: FlashSettings) -> None:
    _validate_probe_tool(settings.tool, settings.probe)

    if settings.tool == "jlink":
        if not settings.jlink.device:
            raise ValueError(
                "[flash.jlink].device is required when tool = 'jlink'. "
                "Run 'mcuenv.py set-target <name>' or set it in mcuenv.project.toml."
            )
        if settings.jlink.interface not in {"swd", "jtag"}:
            raise ValueError(
                f"[flash.jlink].interface must be 'swd' or 'jtag', got '{settings.jlink.interface}'."
            )
        if settings.jlink.speed_khz <= 0:
            raise ValueError("[flash.jlink].speed_khz must be a positive integer (kHz).")
        return

    if settings.tool == "openocd":
        if not settings.openocd.target:
            raise ValueError(
                "[flash.openocd].target is required when tool = 'openocd'. "
                "Run 'mcuenv.py set-target <name>' or set it in mcuenv.project.toml."
            )
        if settings.openocd.adapter != settings.probe:
            raise ValueError(
                f"[flash] probe is '{settings.probe}' but [flash.openocd].adapter is "
                f"'{settings.openocd.adapter}'. They should match."
            )
        return

    if settings.tool == "pyocd":
        if not settings.pyocd.target:
            raise ValueError(
                "[flash.pyocd].target is required when tool = 'pyocd'. "
                "Run 'mcuenv.py set-target <name>' or set it in mcuenv.project.toml."
            )
        return

    raise ValueError(
        f"Unsupported [flash].tool '{settings.tool}'. Use openocd, pyocd, or jlink."
    )


def resolve_flash_settings(
    project: ProjectConfig,
    env: GlobalConfig,
    preset: TargetPreset | None,
) -> FlashSettings:
    tool = (
        project.flash_tool
        or (preset.tool if preset else "")
        or env.default_flash_tool
    )
    probe = (
        project.flash_probe
        or (preset.probe if preset else "")
        or env.default_flash_probe
    )
    after_program = project.flash_after_program or "reset_and_run"
    image = project.flash_image

    preset_jlink = jlink_config_from_preset(preset) if preset else None
    preset_openocd = openocd_config_from_preset(preset) if preset else None
    preset_pyocd = pyocd_config_from_preset(preset) if preset else None

    jlink = _merge_jlink(project.flash_jlink, preset_jlink)
    openocd = _merge_openocd(project.flash_openocd, preset_openocd)
    if probe and not openocd.adapter:
        openocd = replace(openocd, adapter=probe)
    pyocd = _merge_pyocd(project.flash_pyocd, preset_pyocd)

    settings = FlashSettings(
        tool=tool,
        probe=probe,
        after_program=after_program,
        image=image,
        jlink=jlink,
        openocd=openocd,
        pyocd=pyocd,
    )
    _validate_active_tool(settings)
    return settings


def migrate_legacy_flash_section(flash: dict[str, Any]) -> dict[str, Any]:
    """Map flat [flash] keys from older project files into nested tables."""
    migrated = dict(flash)
    jlink = dict(migrated.get("jlink") or {})
    openocd = dict(migrated.get("openocd") or {})
    pyocd = dict(migrated.get("pyocd") or {})

    if "backend" in migrated and "tool" not in migrated:
        migrated["tool"] = migrated["backend"]
    if migrated.get("jlink_device"):
        jlink.setdefault("device", migrated["jlink_device"])
    if migrated.get("speed"):
        jlink.setdefault("speed_khz", migrated["speed"])
    if migrated.get("openocd_target"):
        openocd.setdefault("target", migrated["openocd_target"])
    if migrated.get("openocd_interface"):
        openocd.setdefault("adapter", migrated["openocd_interface"])
    elif migrated.get("interface"):
        openocd.setdefault("adapter", migrated["interface"])
    if migrated.get("pyocd_target"):
        pyocd.setdefault("target", migrated["pyocd_target"])

    migrated["jlink"] = jlink
    migrated["openocd"] = openocd
    migrated["pyocd"] = pyocd
    return migrated
