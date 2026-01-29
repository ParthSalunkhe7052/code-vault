@echo off
title CodeVault - Landing Page, Frontend & Backend
color 0A

echo ========================================
echo  Starting CodeVault Complete Stack
echo ========================================
echo.
echo [1/3] Starting Backend Server (Port 8000)...
echo [2/3] Starting Frontend App (Port 5173)...
echo [3/3] Starting Landing Page (Port 3000)...
echo.
echo Press Ctrl+C to stop all servers
echo ========================================
echo.

:: Change to CodeVaultV1 root directory (one level up from bin)
cd /d "%~dp0.."

:: Start Backend Server in new window
start "CodeVault Backend" cmd /k "cd server && python main.py"

:: Wait 3 seconds for backend to initialize
timeout /t 3 /nobreak >nul

:: Start Frontend in new window
start "CodeVault Frontend" cmd /k "cd frontend && npm run dev"

:: Wait 2 seconds
timeout /t 2 /nobreak >nul

:: Start Landing Page in new window
start "CodeVault Landing Page" cmd /k "cd landing-page && npm run dev"

:: Wait 2 seconds before opening browser
timeout /t 3 /nobreak >nul

:: Open landing page in default browser
start http://localhost:3000

echo.
echo ========================================
echo  All services started successfully!
echo ========================================
echo.
echo  Landing Page: http://localhost:3000
echo  Frontend App: http://localhost:5173
echo  Backend API:  http://localhost:8000
echo.
echo  Close this window to keep services running
echo  Or press any key to exit...
echo ========================================
pause >nul
