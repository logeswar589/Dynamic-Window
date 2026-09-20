@echo off
setlocal enabledelayedexpansion
title DynamicWin
cd /d "%~dp0"

:: ── Check for Python ────────────────────────────────────────────
where py >nul 2>nul
if !errorlevel! equ 0 (
    set PYCMD=py
    set PYWCMD=pyw
    goto :python_found
)

where python >nul 2>nul
if !errorlevel! equ 0 (
    set PYCMD=python
    set PYWCMD=pythonw
    goto :python_found
)

echo.
echo  ERROR: Python is not installed or not on PATH.
echo  Please install Python 3.10+ from https://www.python.org/downloads/
echo  Make sure to check "Add Python to PATH" during installation.
echo.
pause
exit /b 1

:python_found

:: ── Install dependencies if needed ──────────────────────────────
echo Checking dependencies...
!PYCMD! -c "import PySide6; import psutil" >nul 2>nul
if !errorlevel! neq 0 (
    echo Installing dependencies (first run only^)...
    !PYCMD! -m pip install -r requirements.txt --quiet
    if !errorlevel! neq 0 (
        echo.
        echo  ERROR: Failed to install dependencies.
        echo  Try running manually:  !PYCMD! -m pip install -r requirements.txt
        echo.
        pause
        exit /b 1
    )
    echo Dependencies installed successfully!
)

:: ── Launch DynamicWin ───────────────────────────────────────────
echo Starting DynamicWin...
start "" !PYWCMD! main.py
exit
