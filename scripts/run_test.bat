@echo off
REM CodeVault Node.js Build Test Runner
REM Usage: run_test.bat

echo ============================================
echo CodeVault Node.js Build Tester
echo ============================================
echo.

set /p EMAIL="Enter your email: "
set /p PASSWORD="Enter your password: "

echo.
echo Running test...
echo.

python "%~dp0test_nodejs_build.py" --email %EMAIL% --password %PASSWORD% --test simple_console

echo.
pause