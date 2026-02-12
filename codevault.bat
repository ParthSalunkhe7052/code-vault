@echo off
REM ============================================
REM CodeVault CLI Launcher v2.0
REM ============================================

REM Check if arguments were provided
if "%~1"=="" goto :INTERACTIVE_MODE
goto :NORMAL_MODE

:INTERACTIVE_MODE
REM When double-clicked with no arguments, show menu and let user choose
cls
title CodeVault CLI v2.0

echo ============================================
echo    CodeVault CLI v2.0
echo ============================================
echo.
echo Welcome! What would you like to do?
echo.
echo  [1] Login                    (auth login)
echo  [2] List projects            (project list)
echo  [3] Build a project          (project build --interactive)
echo  [4] Check system status      (system status)
echo  [5] Show help                (--help)
echo  [6] Exit
echo.
echo Or type: codevault [command] [args]
echo.

set /p CHOICE="Enter number (1-6): "

if "%CHOICE%"=="1" goto :DO_LOGIN
if "%CHOICE%"=="2" goto :DO_LIST
if "%CHOICE%"=="3" goto :DO_BUILD
if "%CHOICE%"=="4" goto :DO_STATUS
if "%CHOICE%"=="5" goto :DO_HELP
if "%CHOICE%"=="6" goto :DO_EXIT
goto :INTERACTIVE_MODE

:DO_LOGIN
call :RUN_CLI auth login
goto :ASK_CONTINUE

:DO_LIST
call :RUN_CLI project list
goto :ASK_CONTINUE

:DO_BUILD
call :RUN_CLI project build --interactive
goto :ASK_CONTINUE

:DO_STATUS
call :RUN_CLI system status
goto :ASK_CONTINUE

:DO_HELP
call :RUN_CLI --help
goto :ASK_CONTINUE

:DO_EXIT
echo.
echo Goodbye!
timeout /t 1 >nul
exit /b 0

:ASK_CONTINUE
echo.
echo Would you like to run another command? (Y/N)
set /p CONTINUE=""
if /i "%CONTINUE%"=="Y" goto :INTERACTIVE_MODE
if /i "%CONTINUE%"=="YES" goto :INTERACTIVE_MODE
goto :DO_EXIT

:RUN_CLI
REM Subroutine to run CLI with proper setup
cd /d "%~dp0"
set "PYTHONPATH=%CD%\cli;%PYTHONPATH%"
cd cli
python -m codevault_cli %*
exit /b %errorlevel%

:NORMAL_MODE
REM When run from command line with arguments, run normally
setlocal EnableDelayedExpansion

cd /d "%~dp0"
set "PYTHONPATH=%CD%\cli;%PYTHONPATH%"
cd cli

REM Run CLI with provided arguments
python -m codevault_cli %*
set "EXIT_CODE=!ERRORLEVEL!"

REM If error occurred, pause to show it
if !EXIT_CODE! neq 0 (
    echo.
    echo [ERROR] Command failed with code !EXIT_CODE!
    pause
)

endlocal
exit /b %EXIT_CODE%
