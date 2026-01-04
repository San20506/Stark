@echo off
REM Alfred Voice Assistant - Startup Script for Windows
REM Prerequisites: ollama serve running in another terminal

echo.
echo ================================================================
echo                ALFRED VOICE ASSISTANT
echo ================================================================
echo.
echo Starting Alfred... Press Ctrl+C to exit
echo.
echo NOTE: Make sure 'ollama serve' is running in another terminal!
echo.

cd /d "%~dp0"
d:\ALFRED\.venv\Scripts\python.exe main.py

pause
