# Activate the MCU development environment in the current PowerShell session.
# Usage:
#   . D:\mcu-env\export.ps1

$ErrorActionPreference = "Stop"

$MCUENV_ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command python3 -ErrorAction SilentlyContinue
}
if (-not $python) {
    throw "Python 3.11+ is required to activate mcuenv."
}

$exportLines = & $python.Source "$MCUENV_ROOT\mcuenv.py" export --format ps1
Invoke-Expression ($exportLines -join [Environment]::NewLine)

Write-Host "mcuenv activated: $env:MCUENV_ROOT"
