@echo off
chcp 65001 >nul 2>&1
title CodeVault - Web Application Launcher
mode con: cols=100 lines=40
color 0A

:: Get the directory where this script is located
set "ROOT_DIR=%~dp0..\"

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
echo                         Web Application Launcher
echo    ═══════════════════════════════════════════════════════════════════════
echo.

:: Start Backend Server in background
echo    [1/3] Starting Backend Server...
echo          → Activating Python environment
start "CodeVault - Backend" cmd /k "cd /d "%ROOT_DIR%server" && call "%ROOT_DIR%venv\Scripts\activate.bat" && python main.py"

:: Wait for backend to initialize
echo    [■■□□□□□□□□] Backend initializing...
timeout /t 2 /nobreak > nul
echo    [■■■■□□□□□□] Starting frontend...
timeout /t 2 /nobreak > nul

:: Start Frontend Dev Server
echo    [2/3] Starting Frontend Server...
echo          → Launching Vite dev server
start "CodeVault - Frontend" cmd /k "cd /d "%ROOT_DIR%frontend" && npm run dev"

echo    [■■■■■■■□□□] Warming up...
timeout /t 2 /nobreak > nul
echo    [■■■■■■■■■■] Ready!
echo.

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
echo                    ✓ All Services Running Successfully
echo    ═══════════════════════════════════════════════════════════════════════
echo.
echo    ┌──────────────────────────────────────────────────────────────────────┐
echo    │  SERVICE URLS                                                        │
echo    ├──────────────────────────────────────────────────────────────────────┤
echo    │                                                                      │
echo    │   Frontend Dashboard  →  http://localhost:5173                       │
echo    │   Backend API         →  http://localhost:8000                       │
echo    │   API Documentation   →  http://localhost:8000/docs                  │
echo    │                                                                      │
echo    └──────────────────────────────────────────────────────────────────────┘
echo.
echo    ┌──────────────────────────────────────────────────────────────────────┐
echo    │  NOTES                                                               │
echo    ├──────────────────────────────────────────────────────────────────────┤
echo    │                                                                      │
echo    │   • Keep the backend and frontend terminal windows open              │
echo    │   • Use the CLI tool for local compilation: Run CLI.bat              │
echo    │   • Press Ctrl+C in either window to stop the servers                │
echo    │                                                                      │
echo    └──────────────────────────────────────────────────────────────────────┘
echo.
echo    ═══════════════════════════════════════════════════════════════════════
echo.



echo    This window will close in 10 seconds...
timeout /t 10 /nobreak > nul
exit
