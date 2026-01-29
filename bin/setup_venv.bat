@echo off
title Installing CodeVault Dependencies
color 0A

echo.
echo ========================================
echo   Installing CodeVault Dependencies
echo ========================================
echo.

cd /d "%~dp0..\"

echo [1/3] Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo [2/3] Upgrading pip...
python -m pip install --upgrade pip

echo.
echo [3/3] Installing required packages...
pip install -r requirements.txt

echo.
echo ========================================
echo   Installation Complete!
echo ========================================
echo.
echo Press any key to exit...
pause >nul
