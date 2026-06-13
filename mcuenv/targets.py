"""Target presets for STM32 and GD32."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TargetPreset:
    name: str
    family: str
    mcu: str
    cpu: str
    openocd_target: str
    openocd_interface: str = "stlink"
    note: str = ""


TARGETS: dict[str, TargetPreset] = {
    "stm32f103c8": TargetPreset(
        name="stm32f103c8",
        family="stm32",
        mcu="STM32F103C8",
        cpu="cortex-m3",
        openocd_target="stm32f1x",
    ),
    "stm32f303cb": TargetPreset(
        name="stm32f303cb",
        family="stm32",
        mcu="STM32F303CB",
        cpu="cortex-m4",
        openocd_target="stm32f3x",
    ),
    "stm32f407vg": TargetPreset(
        name="stm32f407vg",
        family="stm32",
        mcu="STM32F407VG",
        cpu="cortex-m4",
        openocd_target="stm32f4x",
    ),
    "stm32g431cb": TargetPreset(
        name="stm32g431cb",
        family="stm32",
        mcu="STM32G431CB",
        cpu="cortex-m4",
        openocd_target="stm32g4x",
    ),
    "stm32h743zi": TargetPreset(
        name="stm32h743zi",
        family="stm32",
        mcu="STM32H743ZI",
        cpu="cortex-m7",
        openocd_target="stm32h7x",
    ),
    "gd32f103c8": TargetPreset(
        name="gd32f103c8",
        family="gd32",
        mcu="GD32F103C8",
        cpu="cortex-m3",
        openocd_target="stm32f1x",
        note="GD32F1 is debugged with the STM32F1 OpenOCD target",
    ),
    "gd32f303cc": TargetPreset(
        name="gd32f303cc",
        family="gd32",
        mcu="GD32F303CC",
        cpu="cortex-m4",
        openocd_target="stm32f2x",
        note="GD32F30x is commonly mapped to the STM32F2 OpenOCD target",
    ),
    "gd32f450ik": TargetPreset(
        name="gd32f450ik",
        family="gd32",
        mcu="GD32F450IK",
        cpu="cortex-m4",
        openocd_target="stm32f4x",
        note="GD32F4 is commonly mapped to the STM32F4 OpenOCD target",
    ),
    "gd32e230c8": TargetPreset(
        name="gd32e230c8",
        family="gd32",
        mcu="GD32E230C8",
        cpu="cortex-m23",
        openocd_target="gd32e23x",
    ),
}


def get_target(name: str) -> TargetPreset:
    key = name.lower()
    if key not in TARGETS:
        known = ", ".join(sorted(TARGETS))
        raise KeyError(f"Unknown target '{name}'. Known targets: {known}")
    return TARGETS[key]


def list_targets(family: str | None = None) -> list[TargetPreset]:
    presets = list(TARGETS.values())
    if family is None:
        return presets
    return [preset for preset in presets if preset.family == family.lower()]
