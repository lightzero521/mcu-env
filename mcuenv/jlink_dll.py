"""J-Link ARM DLL (JLinkARM.dll) bindings for flash and erase."""

from __future__ import annotations

import ctypes
import os
import struct
from dataclasses import dataclass
from pathlib import Path

from mcuenv.flash_config import FlashJlinkConfig
from mcuenv.util import FlashProgressBar, is_windows

MAX_ERR_BUF = 336
TIF_JTAG = 0
TIF_SWD = 1
DEFAULT_REMOTE_PORT = 19020

RESET_STRATEGIES = {
    "normal": 0,
    "core": 1,
    "resetpin": 2,
    "connect_under_reset": 3,
}

_LOG_HANDLER = ctypes.CFUNCTYPE(None, ctypes.c_char_p)
_ERR_HANDLER = ctypes.CFUNCTYPE(None, ctypes.c_char_p)
_FLASH_PROGRESS = ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int)


def _cstr(value: bytes | None) -> str:
    if value is None:
        return ""
    return value.decode(errors="replace")


@_FLASH_PROGRESS
def _noop_progress(
    action: bytes,
    progress_string: bytes,
    percentage: int,
) -> None:
    return


class JLinkDllError(RuntimeError):
    pass


@dataclass(frozen=True)
class JLinkDllPaths:
    install_dir: Path
    dll_path: Path


def _python_bitness() -> int:
    return struct.calcsize("P") * 8


def _windows_jlink_dll_names() -> tuple[str, ...]:
    if _python_bitness() == 64:
        return ("JLink_x64.dll", "JLinkARM.dll")
    return ("JLinkARM.dll",)


def _parse_remote_endpoint(ip: str) -> tuple[str, int]:
    """Parse host or host:port for J-Link Remote Server (default port 19020)."""
    value = ip.strip()
    if not value:
        raise ValueError("Remote J-Link ip must not be empty.")

    if value.count(":") == 1:
        host, _, port_text = value.partition(":")
        host = host.strip()
        port_text = port_text.strip()
        if not host:
            raise ValueError(f"Invalid J-Link remote address '{ip}'.")
        if not port_text:
            return host, DEFAULT_REMOTE_PORT
        try:
            port = int(port_text)
        except ValueError as exc:
            raise ValueError(
                f"Invalid J-Link remote port in '{ip}'. Use host or host:port."
            ) from exc
        if port <= 0 or port > 65535:
            raise ValueError(f"J-Link remote port out of range in '{ip}'.")
        return host, port

    # IPv6 or tunnel strings without an explicit trailing :port keep the default port.
    return value, DEFAULT_REMOTE_PORT


def resolve_jlink_dll(configured_dir: Path | None) -> JLinkDllPaths:
    from mcuenv.jlink import jlink_install_path_from_registry

    candidates: list[Path] = []
    if configured_dir is not None:
        candidates.append(configured_dir)
    registry_dir = jlink_install_path_from_registry()
    if registry_dir is not None:
        candidates.append(registry_dir)

    if is_windows():
        dll_names = _windows_jlink_dll_names()
    else:
        dll_names = ("libjlinkarm.so", "libJLinkARM.so")

    last_error: OSError | None = None
    for directory in candidates:
        for name in dll_names:
            dll_path = directory / name
            if not dll_path.is_file():
                continue
            try:
                ctypes.CDLL(str(dll_path))
            except OSError as exc:
                last_error = exc
                continue
            return JLinkDllPaths(install_dir=directory, dll_path=dll_path)

    checked = ", ".join(str(path) for path in candidates) or "(none)"
    if last_error is not None and getattr(last_error, "winerror", None) == 193:
        raise OSError(
            last_error.errno,
            "J-Link DLL architecture does not match Python "
            f"({_python_bitness()}-bit). Install SEGGER J-Link with a matching DLL "
            f"(e.g. JLink_x64.dll) or use 32-bit Python. Checked under {checked}.",
        ) from last_error
    raise FileNotFoundError(
        f"J-Link DLL not found under {checked}. Install SEGGER J-Link or set [paths].jlink."
    )


class JLinkSession:
    """Short-lived J-Link DLL session for programming operations."""

    def __init__(self, dll_paths: JLinkDllPaths) -> None:
        self._paths = dll_paths
        self._dll = ctypes.CDLL(str(dll_paths.dll_path))
        self._progress_bar = FlashProgressBar()
        self._progress_cb = _FLASH_PROGRESS(self._on_progress)
        self._log_cb = _LOG_HANDLER(self._on_log)
        self._err_cb = _ERR_HANDLER(self._on_error)
        self._opened = False
        self._last_error = ""
        self._configure_dll()

    def _configure_dll(self) -> None:
        dll = self._dll
        dll.JLINKARM_OpenEx.restype = ctypes.POINTER(ctypes.c_char)
        dll.JLINKARM_SelectIP.argtypes = [ctypes.c_char_p, ctypes.c_uint32]
        dll.JLINKARM_SelectIP.restype = ctypes.c_int
        dll.JLINKARM_ExecCommand.argtypes = [
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_int,
        ]
        dll.JLINKARM_ExecCommand.restype = ctypes.c_int
        dll.JLINK_DownloadFile.argtypes = [ctypes.c_char_p, ctypes.c_uint32]
        dll.JLINK_DownloadFile.restype = ctypes.c_int
        dll.JLINK_EraseChip.restype = ctypes.c_int
        dll.JLINK_SetFlashProgProgressCallback.argtypes = [_FLASH_PROGRESS]
        dll.JLINK_SetFlashProgProgressCallback.restype = None

    def _on_log(self, message: bytes) -> None:
        return

    def _on_error(self, message: bytes | None) -> None:
        text = _cstr(message).strip()
        if text:
            self._last_error = text

    def _on_progress(
        self,
        action: bytes | None,
        progress_string: bytes | None,
        percentage: int,
    ) -> None:
        self._progress_bar.update(
            _cstr(action),
            _cstr(progress_string),
            int(percentage),
        )

    def _clear_progress_callback(self) -> None:
        self._dll.JLINK_SetFlashProgProgressCallback(_noop_progress)

    def open(self, *, serial: str = "", ip: str = "") -> None:
        if self._opened:
            return

        dll = self._dll
        if ip:
            try:
                host, port = _parse_remote_endpoint(ip)
            except ValueError as exc:
                raise JLinkDllError(str(exc)) from exc
            result = dll.JLINKARM_SelectIP(host.encode("utf-8"), port)
            if result != 0:
                raise JLinkDllError(
                    f"Could not select J-Link Remote Server at {host}:{port}."
                )
        elif serial:
            result = dll.JLINKARM_EMU_SelectByUSBSN(int(serial))
            if result < 0:
                raise JLinkDllError(f"No J-Link with serial number {serial}.")
        else:
            result = dll.JLINKARM_SelectUSB(0)
            if result != 0:
                raise JLinkDllError("Could not connect to default J-Link emulator.")

        error = dll.JLINKARM_OpenEx(self._log_cb, self._err_cb)
        error_text = ctypes.cast(error, ctypes.c_char_p).value
        if error_text is not None:
            raise JLinkDllError(error_text.decode(errors="replace"))

        self._exec_command("SetBatchMode = 1")
        self._exec_command("DisableInfoWinFlashDL")
        self._exec_command("DisableInfoWinFlashBPs")
        self._opened = True

    def close(self) -> None:
        if not self._opened:
            return
        self._dll.JLINKARM_Close()
        self._opened = False

    def __enter__(self) -> JLinkSession:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _exec_command(self, command: str) -> None:
        err_buf = (ctypes.c_char * MAX_ERR_BUF)()
        result = self._dll.JLINKARM_ExecCommand(command.encode(), err_buf, MAX_ERR_BUF)
        err_text = ctypes.string_at(err_buf).decode(errors="replace").strip()
        if err_text:
            raise JLinkDllError(err_text)
        if result < 0:
            raise JLinkDllError(f"J-Link command failed ({result}): {command}")

    def connect(self, config: FlashJlinkConfig) -> None:
        interface = config.interface.lower()
        tif = TIF_SWD if interface == "swd" else TIF_JTAG
        if self._dll.JLINKARM_TIF_Select(tif) != 0:
            raise JLinkDllError(f"Failed to select interface '{interface}'.")

        if config.reset_strategy:
            strategy = RESET_STRATEGIES.get(config.reset_strategy.lower())
            if strategy is None:
                raise JLinkDllError(
                    f"Unknown reset_strategy '{config.reset_strategy}'. "
                    f"Use one of: {', '.join(RESET_STRATEGIES)}."
                )
            self._dll.JLINKARM_SetResetType(strategy)

        if config.script:
            script_path = Path(config.script)
            if not script_path.is_file():
                raise FileNotFoundError(f"J-Link script not found: {script_path}")
            self._exec_command(f"scriptfile = {script_path.as_posix()}")

        self._exec_command(f"Device = {config.device}")
        self._dll.JLINKARM_SetSpeed(int(config.speed_khz))

        if not self._dll.JLINKARM_IsConnected():
            result = self._dll.JLINKARM_Connect()
            if result < 0:
                raise JLinkDllError(f"Failed to connect to target (code {result}).")

        try:
            self._dll.JLINKARM_Halt()
        except Exception:
            pass

    def flash_file(self, firmware: Path, *, after_program: str) -> None:
        firmware = firmware.resolve()
        if not firmware.is_file():
            raise FileNotFoundError(f"Firmware not found: {firmware}")

        self._dll.JLINK_SetFlashProgProgressCallback(self._progress_cb)
        try:
            result = self._dll.JLINK_DownloadFile(
                os.fsencode(str(firmware)),
                0,
            )
            if result < 0:
                raise JLinkDllError(self._flash_error_message(result))
        finally:
            self._clear_progress_callback()
            self._progress_bar.finish()

        self._apply_after_program(after_program)

    def erase_chip(self) -> None:
        self._dll.JLINK_SetFlashProgProgressCallback(self._progress_cb)
        try:
            result = self._dll.JLINK_EraseChip()
            if result < 0:
                raise JLinkDllError(self._erase_error_message(result))
        finally:
            self._clear_progress_callback()
            self._progress_bar.finish()

    def _apply_after_program(self, after_program: str) -> None:
        if after_program == "none":
            return
        halt = after_program == "reset_halt"
        result = self._dll.JLINKARM_Reset()
        if result < 0:
            raise JLinkDllError(f"Reset failed (code {result}).")
        if not halt:
            self._dll.JLINKARM_Go()

    @staticmethod
    def _flash_error_message(code: int) -> str:
        messages = {
            -2: "Flash compare failed.",
            -3: "Flash program/erase failed.",
            -4: "Flash verify failed.",
            -268: "Could not open firmware file.",
            -269: "Unknown firmware file format.",
        }
        return messages.get(code, f"Flash download failed (code {code}).")

    @staticmethod
    def _erase_error_message(code: int) -> str:
        if code == -5:
            return "Chip erase failed."
        return f"Chip erase failed (code {code})."


def run_jlink_flash(
    config: FlashJlinkConfig,
    firmware: Path,
    *,
    configured_dir: Path | None,
    after_program: str,
) -> None:
    paths = resolve_jlink_dll(configured_dir)
    with JLinkSession(paths) as session:
        session.open(serial=config.serial, ip=config.ip)
        session.connect(config)
        session.flash_file(firmware, after_program=after_program)


def run_jlink_erase(
    config: FlashJlinkConfig,
    *,
    configured_dir: Path | None,
) -> None:
    paths = resolve_jlink_dll(configured_dir)
    with JLinkSession(paths) as session:
        session.open(serial=config.serial, ip=config.ip)
        session.connect(config)
        session.erase_chip()
