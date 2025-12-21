@echo off
REM License Wrapper CLI Compiler - Windows Launcher
REM Usage: lw-compiler.bat [command] [args]

setlocal

REM Change to script directory
cd /d "%~dp0"

REM Run the Python script with all arguments
python lw_compiler.py %*

endlocal
