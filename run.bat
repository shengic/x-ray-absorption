@echo off
REM  version 1.0 by Albert Sheng
REM  Cross-drive portable launcher. Works from any drive letter.
REM  Delegates to bootstrap.py which self-heals .venv when needed.

setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo Python is not on PATH.
    echo Install Python 3.12 from https://www.python.org/downloads/
    echo Make sure to tick "Add python.exe to PATH" during install.
    echo.
    pause
    exit /b 1
)

python bootstrap.py %*
endlocal
