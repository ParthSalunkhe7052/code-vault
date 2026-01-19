@echo off
echo Starting CodeVault Servers...

:: Start Backend
echo Starting Backend...
start "CodeVault Backend" cmd /k "call venv\Scripts\activate && cd server && python main.py"

:: Start Frontend
echo Starting Frontend...
start "CodeVault Frontend" cmd /k "cd frontend && npm run dev"

echo Servers launched in separate windows.
