# Activate the MCU development environment in the current PowerShell session.
# Usage:
#   . D:\mcu-env\export.ps1
#
# After activation:
#   mcuenv.py doctor
#   mcuenv.py build
#   deactivate

$ErrorActionPreference = "Stop"

$MCUENV_ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command python3 -ErrorAction SilentlyContinue
}
if (-not $python) {
    throw "Python 3.11+ is required to activate mcuenv."
}

$global:MCUENV_PYTHON = $python.Source

if ($env:MCUENV_ACTIVE -eq "1") {
    Write-Warning "mcuenv is already active. Run 'deactivate' first."
    return
}

$env:MCUENV_OLD_PATH = $env:PATH
foreach ($name in @("OPENOCD_SCRIPTS", "CMAKE_TOOLCHAIN_FILE")) {
    $backup = "MCUENV_OLD_$name"
    if (Test-Path "env:$name") {
        Set-Item "env:$backup" -Value (Get-Item "env:$name").Value
    } else {
        Remove-Item "env:$backup" -ErrorAction SilentlyContinue
    }
}

if (-not (Test-Path variable:global:MCUENV_OLD_PROMPT)) {
    $global:MCUENV_OLD_PROMPT = $function:prompt
}

$exportLines = & $global:MCUENV_PYTHON "$MCUENV_ROOT\mcuenv.py" export --format ps1
Invoke-Expression ($exportLines -join [Environment]::NewLine)

$global:MCUENV_PROMPT_SEGMENT = (& $global:MCUENV_PYTHON "$MCUENV_ROOT\mcuenv.py" prompt-segment --format ps1).TrimEnd()
function global:prompt {
    $base = & $global:MCUENV_OLD_PROMPT
    return "$($global:MCUENV_PROMPT_SEGMENT)$base"
}

function global:deactivate {
    if ($env:MCUENV_ACTIVE -ne "1") {
        Write-Warning "mcuenv is not active."
        return
    }

    $deactivateLines = & $global:MCUENV_PYTHON "$env:MCUENV_ROOT\mcuenv.py" deactivate --format ps1
    Invoke-Expression ($deactivateLines -join [Environment]::NewLine)
}

function global:mcuenv.py {
    [CmdletBinding()]
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$Args
    )

    if ($Args.Count -gt 0 -and $Args[0] -eq "deactivate") {
        deactivate
        return
    }

    & $global:MCUENV_PYTHON "$env:MCUENV_ROOT\mcuenv.py" @Args
}

$env:MCUENV_ACTIVE = "1"

Write-Host "mcuenv activated: $env:MCUENV_ROOT"
Write-Host "Run 'mcuenv.py doctor' to verify the environment."
Write-Host "Run 'deactivate' when you want to leave this environment."
