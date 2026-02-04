@echo off
REM ============================================
REM CodeVault - Complete Startup Script
REM ============================================
REM This script starts the backend, frontend, and opens the landing page
REM Author: CodeVault Team
REM Last Updated: 2026-02-04

SETLOCAL EnableDelayedExpansion

echo.
echo ============================================
echo   CodeVault - Starting All Services
echo ============================================
echo.

REM Get the script directory
SET "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

REM Color codes for better output (using findstr workaround)
SET "SUCCESS_ICON=[92m[+][0m"
SET "ERROR_ICON=[91m[X][0m"
SET "INFO_ICON=[94m[*][0m"

echo %INFO_ICON% Root Directory: %ROOT_DIR%
echo.

REM ============================================
REM Step 1: Check Prerequisites
REM ============================================
echo [1/5] Checking Prerequisites...
echo.

REM Check if Python is installed
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo %ERROR_ICON% Python is not installed or not in PATH!
    echo Please install Python 3.11+ from https://www.python.org/
    pause
    exit /b 1
)
echo %SUCCESS_ICON% Python is installed

REM Check if Node.js is installed
node --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo %ERROR_ICON% Node.js is not installed or not in PATH!
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)
echo %SUCCESS_ICON% Node.js is installed

REM Check if npm is installed
npm --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo %ERROR_ICON% npm is not installed!
    pause
    exit /b 1
)
echo %SUCCESS_ICON% npm is installed
echo.

REM ============================================
REM Step 2: Install Dependencies (if needed)
REM ============================================
echo [2/5] Checking Dependencies...
echo.

REM Check backend dependencies
IF NOT EXIST "server\__pycache__\" (
    echo %INFO_ICON% Installing backend dependencies...
    cd server
    pip install -r requirements.txt --quiet
    cd ..
    echo %SUCCESS_ICON% Backend dependencies installed
) ELSE (
    echo %SUCCESS_ICON% Backend dependencies already installed
)

REM Check frontend dependencies
IF NOT EXIST "frontend\node_modules\" (
    echo %INFO_ICON% Installing frontend dependencies...
    cd frontend
    call npm install
    cd ..
    echo %SUCCESS_ICON% Frontend dependencies installed
) ELSE (
    echo %SUCCESS_ICON% Frontend dependencies already installed
)

REM Check landing page dependencies
IF NOT EXIST "landing-page\node_modules\" (
    echo %INFO_ICON% Installing landing page dependencies...
    cd landing-page
    call npm install
    cd ..
    echo %SUCCESS_ICON% Landing page dependencies installed
) ELSE (
    echo %SUCCESS_ICON% Landing page dependencies already installed
)
echo.

REM ============================================
REM Step 3: Start Backend Server
REM ============================================
echo [3/5] Starting Backend Server...
echo.

REM Kill any existing Python processes on port 8000
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    echo %INFO_ICON% Killing existing process on port 8000...
    taskkill /F /PID %%a >nul 2>&1
)

REM Start backend in a new window
echo %INFO_ICON% Launching backend server (Port 8000)...
start "CodeVault Backend" cmd /k "cd /d "%ROOT_DIR%server" && python main.py"

REM Wait for backend to start
echo %INFO_ICON% Waiting for backend to initialize...
timeout /t 3 /nobreak >nul

REM Check if backend is running
curl -s http://127.0.0.1:8000/api/v1/status >nul 2>&1
IF ERRORLEVEL 1 (
    echo %ERROR_ICON% Backend failed to start! Check the backend window for errors.
    pause
    exit /b 1
)
echo %SUCCESS_ICON% Backend is running on http://127.0.0.1:8000
echo.

REM ============================================
REM Step 4: Start Frontend & Landing Page
REM ============================================
echo [4/5] Starting Frontend Services...
echo.

REM Kill any existing processes on ports 5173 and 3000
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5173 ^| findstr LISTENING') do (
    echo %INFO_ICON% Killing existing process on port 5173...
    taskkill /F /PID %%a >nul 2>&1
)

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000 ^| findstr LISTENING') do (
    echo %INFO_ICON% Killing existing process on port 3000...
    taskkill /F /PID %%a >nul 2>&1
)

REM Start frontend dashboard in a new window
echo %INFO_ICON% Launching frontend dashboard (Port 5173)...
start "CodeVault Frontend" cmd /k "cd /d "%ROOT_DIR%frontend" && npm run dev"

REM Wait a bit before starting landing page
timeout /t 2 /nobreak >nul

REM Start landing page in a new window
echo %INFO_ICON% Launching landing page (Port 3000)...
start "CodeVault Landing Page" cmd /k "cd /d "%ROOT_DIR%landing-page" && npm run dev"

REM Wait for services to fully start
echo %INFO_ICON% Waiting for services to initialize...
timeout /t 5 /nobreak >nul

echo %SUCCESS_ICON% Frontend is running on http://localhost:5173
echo %SUCCESS_ICON% Landing page is running on http://localhost:3000
echo.

REM ============================================
REM Step 5: Open Landing Page in Browser
REM ============================================
echo [5/5] Opening Landing Page...
echo.

REM Wait a moment to ensure landing page is ready
timeout /t 2 /nobreak >nul

REM Open landing page in default browser
echo %INFO_ICON% Opening http://localhost:3000 in your browser...
start http://localhost:3000

echo.
echo ============================================
echo   CodeVault is Ready!
echo ============================================
echo.
echo Services Running:
echo   - Backend API:      http://127.0.0.1:8000
echo   - Frontend App:     http://localhost:5173
echo   - Landing Page:     http://localhost:3000
echo.
echo %SUCCESS_ICON% All services started successfully!
echo.
echo To stop all services:
echo   1. Close the Backend, Frontend, and Landing Page windows
echo   OR
echo   2. Press Ctrl+C in each window
echo.
echo ============================================
echo.

pause
