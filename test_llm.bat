@echo off
cd /d %~dp0
call notion_sync_env\Scripts\activate

echo Testing Ollama connection...
python test_ollama.py
if errorlevel 1 (
    echo Failed to connect to Ollama
    pause
    exit /b 1
)

echo Ollama connection successful
pause 