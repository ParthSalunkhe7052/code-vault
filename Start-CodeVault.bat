@echo off
REM ============================================
REM CodeVault - Simple Startup Script
REM ============================================

echo.
echo Starting CodeVault...
echo.

REM Get script directory
SET SCRIPT_DIR=%~dp0

REM Kill existing processes on ports
echo Killing existing processes...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5173 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1

echo.
echo Starting Backend (Port 8000)...
start "CodeVault Backend" cmd /k "cd /d "%SCRIPT_DIR%server" && python main.py"

timeout /t 2 /nobreak >nul

echo Starting Frontend Dashboard (Port 5173)...
start "CodeVault Dashboard" cmd /k "cd /d "%SCRIPT_DIR%frontend" && npm run dev"

timeout /t 2 /nobreak >nul

echo Starting Landing Page (Port 3000)...
start "CodeVault Landing" cmd /k "cd /d "%SCRIPT_DIR%landing-page" && npm run dev"

timeout /t 5 /nobreak >nul

echo.
echo Opening browser...
start http://localhost:3000

echo.
echo ============================================
echo CodeVault Started!
echo ============================================
echo.
echo Backend:       http://127.0.0.1:8000
echo Dashboard:     http://localhost:5173
echo Landing Page:  http://localhost:3000
echo.
echo Check the opened windows for any errors.
echo Close those windows to stop the services.
echo.
pause
