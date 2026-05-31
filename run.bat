@echo off
REM Code Agent — Windows launcher
REM Double-click this file or run from cmd/PowerShell

setlocal enabledelayedexpansion

echo.
echo ================================================
echo   Code Agent — Claude Code Clone (Free AI)
echo ================================================
echo.

REM Check Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH.
    echo Download Python from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

REM Show Python version
for /f "tokens=*" %%i in ('python --version') do set PYVER=%%i
echo Using: %PYVER%

REM Check if we're in the right directory
if not exist "main.py" (
    echo ERROR: main.py not found.
    echo Please run this script from the code-agent directory.
    pause
    exit /b 1
)

REM Install dependencies if needed
if not exist ".deps_installed" (
    echo.
    echo Installing dependencies...
    pip install -r requirements.txt
    if %errorlevel% equ 0 (
        echo 1 > .deps_installed
        echo Dependencies installed successfully!
    ) else (
        echo WARNING: Some dependencies may not have installed correctly.
        echo Try running: pip install rich python-dotenv
    )
)

REM Check for .env file
if not exist ".env" (
    echo.
    echo No .env file found. Running setup wizard...
    echo.
    python main.py --setup
    echo.
)

REM Parse arguments
set ARGS=%*

echo.
echo Starting Code Agent...
echo Workspace: %CD%
echo.

REM Run the agent
python main.py %ARGS%

if %errorlevel% neq 0 (
    echo.
    echo Agent exited with error code %errorlevel%
    pause
)
