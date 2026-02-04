@echo off
REM ============================================
REM CodeVault - Quick Start Script
REM ============================================
title CodeVault Launcher

echo.
echo ============================================
echo   CodeVault - Starting All Services
echo ============================================
echo.

REM Get script directory
SET SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

echo [*] Working Directory: %CD%
echo.

REM ============================================
REM Check Prerequisites
REM ============================================
echo [1/5] Checking Prerequisites...

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Install from https://python.org
    pause
    exit /b 1
)
echo [OK] Python installed

node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found! Install from https://nodejs.org
    pause
    exit /b 1
)
echo [OK] Node.js installed
echo.

REM ============================================
REM Install Dependencies if Needed
REM ============================================
echo [2/5] Checking Dependencies...

if not exist "server\requirements.txt" (
    echo [ERROR] server\requirements.txt not found!
    pause
    exit /b 1
)

if not exist "frontend\package.json" (
    echo [ERROR] frontend\package.json not found!
    pause
    exit /b 1
)

if not exist "landing-page\package.json" (
    echo [ERROR] landing-page\package.json not found!
    pause
    exit /b 1
)

REM Check if node_modules exist
if not exist "frontend\node_modules\" (
    echo [*] Installing frontend dependencies...
    cd frontend
    call npm install --silent
    cd ..
)
echo [OK] Frontend dependencies ready

if not exist "landing-page\node_modules\" (
    echo [*] Installing landing page dependencies...
    cd landing-page
    call npm install --silent
    cd ..
)
echo [OK] Landing page dependencies ready
echo.

REM ============================================
REM Start Backend Server
REM ============================================
echo [3/5] Starting Backend Server (Port 8000)...

REM Kill existing processes on port 8000
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)

REM Start backend in new window
start "CodeVault Backend" cmd /c "cd /d "%SCRIPT_DIR%server" && python main.py"

REM Wait for backend to start
timeout /t 3 /nobreak >nul
echo [OK] Backend starting...
echo.

REM ============================================
REM Start Frontend Services
REM ============================================
echo [4/5] Starting Frontend Services...

REM Kill existing processes on ports 5173 and 3000
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5173 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)

REM Start frontend dashboard
start "CodeVault Dashboard" cmd /c "cd /d "%SCRIPT_DIR%frontend" && npm run dev"
timeout /t 2 /nobreak >nul
echo [OK] Dashboard starting (Port 5173)...

REM Start landing page
start "CodeVault Landing" cmd /c "cd /d "%SCRIPT_DIR%landing-page" && npm run dev"
timeout /t 2 /nobreak >nul
echo [OK] Landing page starting (Port 3000)...
echo.

REM ============================================
REM Open Browser
REM ============================================
echo [5/5] Opening Browser...

REM Wait for landing page to be ready
timeout /t 5 /nobreak >nul

start http://localhost:3000
echo [OK] Browser opened
echo.

echo ============================================
echo   CodeVault is Running!
echo ============================================
echo.
echo Services:
echo   Backend:       http://127.0.0.1:8000
echo   Dashboard:     http://localhost:5173
echo   Landing Page:  http://localhost:3000
echo.
echo Press any key to keep this window open...
echo (Close the other windows to stop services)
echo.
pause
