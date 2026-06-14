"""Shell activation helpers for export scripts."""

from __future__ import annotations

from mcuenv.env import MANAGED_ENV_VARS

_ENV_VARS = MANAGED_ENV_VARS


def deactivate_lines(fmt: str) -> list[str]:
    if fmt in {"ps1", "powershell"}:
        return _deactivate_ps1()
    if fmt in {"bash", "sh"}:
        return _deactivate_bash()
    raise ValueError(f"Unsupported deactivate format: {fmt}")


def _deactivate_ps1() -> list[str]:
    lines = [
        'if ($env:MCUENV_ACTIVE -ne "1") {',
        '    Write-Warning "mcuenv is not active."',
        "    return",
        "}",
        'if ($env:MCUENV_OLD_PATH) { $env:PATH = $env:MCUENV_OLD_PATH }',
    ]
    for name in _ENV_VARS:
        backup = f"MCUENV_OLD_{name}"
        lines.extend(
            [
                f'if (Test-Path "env:{backup}") {{',
                f'    Set-Item "env:{name}" -Value (Get-Item "env:{backup}").Value',
                f'    Remove-Item "env:{backup}"',
                "} else {",
                f'    Remove-Item "env:{name}" -ErrorAction SilentlyContinue',
                "}",
            ]
        )
    lines.extend(
        [
            'Remove-Item env:MCUENV_ROOT -ErrorAction SilentlyContinue',
            'Remove-Item env:MCUENV_ACTIVE -ErrorAction SilentlyContinue',
            'Remove-Item env:MCUENV_OLD_PATH -ErrorAction SilentlyContinue',
            'Remove-Item variable:global:MCUENV_PROMPT_SEGMENT -ErrorAction SilentlyContinue',
            'Remove-Item variable:global:MCUENV_PYTHON -ErrorAction SilentlyContinue',
            "if ($global:MCUENV_OLD_PROMPT) {",
            "    $function:prompt = $global:MCUENV_OLD_PROMPT",
            "    Remove-Item variable:global:MCUENV_OLD_PROMPT -ErrorAction SilentlyContinue",
            "}",
            "Remove-Item function:mcuenv.py -ErrorAction SilentlyContinue",
            "Remove-Item function:deactivate -ErrorAction SilentlyContinue",
            'Write-Host "mcuenv deactivated."',
        ]
    )
    return lines


def _deactivate_bash() -> list[str]:
    lines = [
        'if [[ "${MCUENV_ACTIVE:-}" != "1" ]]; then',
        '  echo "mcuenv is not active." >&2',
        "  return 0",
        "fi",
        'if [[ -n "${MCUENV_OLD_PATH:-}" ]]; then',
        '  export PATH="$MCUENV_OLD_PATH"',
        "fi",
    ]
    for name in _ENV_VARS:
        backup = f"MCUENV_OLD_{name}"
        lines.extend(
            [
                f'if [[ -n "${{{backup}:-}}" ]]; then',
                f'  export {name}="${{{backup}}}"',
                f"  unset {backup}",
                "else",
                f"  unset {name}",
                "fi",
            ]
        )
    lines.extend(
        [
            "unset MCUENV_ROOT MCUENV_ACTIVE MCUENV_OLD_PATH",
            'if [[ -n "${MCUENV_OLD_PS1:-}" ]]; then',
            '  export PS1="$MCUENV_OLD_PS1"',
            "  unset MCUENV_OLD_PS1",
            "fi",
            "unset -f mcuenv.py deactivate 2>/dev/null || true",
            'echo "mcuenv deactivated."',
        ]
    )
    return lines
