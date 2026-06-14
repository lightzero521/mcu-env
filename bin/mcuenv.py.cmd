@echo off
setlocal EnableExtensions
set "MCUENV_BIN=%~dp0"
for %%I in ("%MCUENV_BIN%..") do set "MCUENV_ROOT=%%~fI"
where python >nul 2>&1
if %ERRORLEVEL%==0 (
  python "%MCUENV_ROOT%\mcuenv.py" %*
  exit /b %ERRORLEVEL%
)
where python3 >nul 2>&1
if %ERRORLEVEL%==0 (
  python3 "%MCUENV_ROOT%\mcuenv.py" %*
  exit /b %ERRORLEVEL%
)
echo Python 3.11+ is required for mcuenv.py>&2
exit /b 1
