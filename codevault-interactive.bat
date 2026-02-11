@echo off
REM ============================================
REM CodeVault CLI - Interactive Mode
REM Double-click this to use the CLI interactively
REM ============================================

title CodeVault CLI v2.0 - Interactive Mode
cls

echo ============================================
echo    CodeVault CLI v2.0
echo ============================================
echo.

REM Change to script directory
cd /d "%~dp0"

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed!
    echo Please install Python from: https://python.org
    pause
    exit /b 1
)

REM Set Python path
set "PYTHONPATH=%CD%\cli;%PYTHONPATH%"
cd cli

:MENU
cls
echo ============================================
echo    CodeVault CLI v2.0
echo ============================================
echo.
echo Available Commands:
echo.
echo  [1] auth login       - Login to your account
echo  [2] auth logout      - Logout
echo  [3] auth whoami      - Show user info
echo  [4] project list     - List your projects
echo  [5] project build    - Build a project (interactive)
echo  [6] system status    - Check system status
echo  [7] system version   - Show version
echo  [8] help             - Show detailed help
echo  [0] exit             - Close this window
echo.
echo Or type any command directly (e.g., "project build my-project-id --fast")
echo.

set /p COMMAND="Enter command or number: "

if "%COMMAND%"=="0" goto :EXIT
if "%COMMAND%"=="1" goto :AUTH_LOGIN
if "%COMMAND%"=="2" goto :AUTH_LOGOUT
if "%COMMAND%"=="3" goto :AUTH_WHOAMI
if "%COMMAND%"=="4" goto :PROJECT_LIST
if "%COMMAND%"=="5" goto :PROJECT_BUILD
if "%COMMAND%"=="6" goto :SYSTEM_STATUS
if "%COMMAND%"=="7" goto :SYSTEM_VERSION
if "%COMMAND%"=="8" goto :HELP
if "%COMMAND%"=="exit" goto :EXIT
if "%COMMAND%"=="quit" goto :EXIT

REM If user typed a custom command, run it
if not "%COMMAND%"=="" goto :RUN_CUSTOM

goto :MENU

:AUTH_LOGIN
echo.
echo Running: codevault auth login
python -m codevault_cli auth login
goto :PAUSE_AND_RETURN

:AUTH_LOGOUT
echo.
echo Running: codevault auth logout
echo Are you sure you want to logout? (Y/N)
set /p CONFIRM=""
if /i "%CONFIRM%"=="Y" (
    python -m codevault_cli auth logout
)
goto :PAUSE_AND_RETURN

:AUTH_WHOAMI
echo.
echo Running: codevault auth whoami
python -m codevault_cli auth whoami
goto :PAUSE_AND_RETURN

:PROJECT_LIST
echo.
echo Running: codevault project list
python -m codevault_cli project list
goto :PAUSE_AND_RETURN

:PROJECT_BUILD
echo.
echo Build Options:
echo  [1] Interactive build (select project with prompts)
echo  [2] Build specific project (enter project ID)
echo  [3] Build local file (enter file path)
echo  [0] Cancel
set /p BUILD_CHOICE="Choose option: "

if "%BUILD_CHOICE%"=="1" (
    echo.
    echo Running: codevault project build --interactive
    python -m codevault_cli project build --interactive
) else if "%BUILD_CHOICE%"=="2" (
    echo.
    set /p PROJECT_ID="Enter project ID: "
    if not "!PROJECT_ID!"=="" (
        echo Running: codevault project build !PROJECT_ID!
        python -m codevault_cli project build !PROJECT_ID!
    )
) else if "%BUILD_CHOICE%"=="3" (
    echo.
    set /p FILE_PATH="Enter file path (e.g., .\\main.py): "
    if not "!FILE_PATH!"=="" (
        echo Running: codevault project build !FILE_PATH!
        python -m codevault_cli project build !FILE_PATH!
    )
)
goto :PAUSE_AND_RETURN

:SYSTEM_STATUS
echo.
echo Running: codevault system status
python -m codevault_cli system status
goto :PAUSE_AND_RETURN

:SYSTEM_VERSION
echo.
echo Running: codevault system version
python -m codevault_cli system version
goto :PAUSE_AND_RETURN

:HELP
echo.
echo Showing help...
python -m codevault_cli --help
goto :PAUSE_AND_RETURN

:RUN_CUSTOM
echo.
echo Running: codevault %COMMAND%
python -m codevault_cli %COMMAND%
goto :PAUSE_AND_RETURN

:PAUSE_AND_RETURN
echo.
echo ============================================
echo Command completed.
echo ============================================
echo.
echo Press any key to return to menu...
pause >nul
goto :MENU

:EXIT
echo.
echo Thank you for using CodeVault CLI!
echo.
echo Press any key to close...
pause >nul
exit /b 0
