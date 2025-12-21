@echo off
title CodeVault - Desktop App Launcher
color 0B

echo ============================================
echo    CodeVault Desktop App - Starting
echo ============================================
echo.

:: Get the directory where this script is located
set "ROOT_DIR=%~dp0"

:: Start Backend Server in background
echo [1/3] Starting Backend Server...
start "CodeVault - Backend" cmd /k "cd /d "%ROOT_DIR%CodeVaultV1\server" && "%ROOT_DIR%venv\Scripts\activate.bat" && python main.py"

:: Wait for backend to initialize
echo       Waiting for backend to start...
timeout /t 4 /nobreak > nul

:: Start Frontend Dev Server in background
echo [2/3] Starting Frontend Server...
start "CodeVault - Frontend" cmd /k "cd /d "%ROOT_DIR%CodeVaultV1\frontend" && npm run dev"

:: Wait for frontend to initialize
echo       Waiting for frontend to start...
timeout /t 5 /nobreak > nul

:: Start Tauri Desktop App
echo [3/3] Launching Desktop App...
start "CodeVault - Desktop" cmd /k "cd /d "%ROOT_DIR%CodeVaultV1" && cargo tauri dev --no-dev-server"

echo.
echo ============================================
echo    CodeVault Desktop App Starting!
echo ============================================
echo.
echo    Backend:     http://localhost:8000
echo    Frontend:    http://localhost:5173
echo    Desktop App: Opening soon...
echo.
echo    THREE WINDOWS WILL OPEN:
echo    - Backend server (keep open)
echo    - Frontend server (keep open)
echo    - Desktop app window
echo.
echo    (This window will close in 3 seconds)
echo ============================================

timeout /t 3 /nobreak > nul

