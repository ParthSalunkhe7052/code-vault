@echo off
chcp 65001 >nul 2>&1
title CodeVault CLI - Professional License Protection
mode con: cols=100
color 0A

:: Get the directory where this script is located
set "ROOT_DIR=%~dp0"

cls
echo.
echo.
echo    ██████╗ ██████╗ ██████╗ ███████╗██╗   ██╗ █████╗ ██╗   ██╗██╗  ████████╗
echo   ██╔════╝██╔═══██╗██╔══██╗██╔════╝██║   ██║██╔══██╗██║   ██║██║  ╚══██╔══╝
echo   ██║     ██║   ██║██║  ██║█████╗  ██║   ██║███████║██║   ██║██║     ██║   
echo   ██║     ██║   ██║██║  ██║██╔══╝  ╚██╗ ██╔╝██╔══██║██║   ██║██║     ██║   
echo   ╚██████╗╚██████╔╝██████╔╝███████╗ ╚████╔╝ ██║  ██║╚██████╔╝███████╗██║   
echo    ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝  ╚═══╝  ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝   
echo.
echo    ═══════════════════════════════════════════════════════════════════════
echo                   Professional License Protection System
echo    ═══════════════════════════════════════════════════════════════════════
echo.
echo.

:: Brief loading animation
echo    [■□□□□□□□□□] Initializing...
timeout /t 1 /nobreak >nul
cls

echo.
echo    ██████╗ ██████╗ ██████╗ ███████╗██╗   ██╗ █████╗ ██╗   ██╗██╗  ████████╗
echo   ██╔════╝██╔═══██╗██╔══██╗██╔════╝██║   ██║██╔══██╗██║   ██║██║  ╚══██╔══╝
echo   ██║     ██║   ██║██║  ██║█████╗  ██║   ██║███████║██║   ██║██║     ██║   
echo   ██║     ██║   ██║██║  ██║██╔══╝  ╚██╗ ██╔╝██╔══██║██║   ██║██║     ██║   
echo   ╚██████╗╚██████╔╝██████╔╝███████╗ ╚████╔╝ ██║  ██║╚██████╔╝███████╗██║   
echo    ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝  ╚═══╝  ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝   
echo.
echo    ═══════════════════════════════════════════════════════════════════════
echo                   Professional License Protection System
echo    ═══════════════════════════════════════════════════════════════════════
echo.
echo    [■■■■■■■■■■] Ready!
echo.
echo    ┌──────────────────────────────────────────────────────────────────────┐
echo    │  COMMANDS                                                            │
echo    ├──────────────────────────────────────────────────────────────────────┤
echo    │                                                                      │
echo    │   python lw_compiler.py login     →  Authenticate with CodeVault    │
echo    │   python lw_compiler.py build     →  Compile your project            │
echo    │   python lw_compiler.py status    →  Check system requirements       │
echo    │   python lw_compiler.py projects  →  List your projects              │
echo    │   python lw_compiler.py logout    →  Clear saved credentials         │
echo    │                                                                      │
echo    └──────────────────────────────────────────────────────────────────────┘
echo.

cd /d "%ROOT_DIR%cli"

:: Show Python version
echo    Activating virtual environment...
if exist "%ROOT_DIR%venv\Scripts\activate.bat" (
    call "%ROOT_DIR%venv\Scripts\activate.bat"
    echo    [OK] Virtual environment loaded
    echo    Python version:
    python --version
) else (
    echo    [!] No virtual environment found, using system Python
)

echo.
echo    ═══════════════════════════════════════════════════════════════════════
echo.

:: Keep the window open for interaction with venv active
cmd /k
