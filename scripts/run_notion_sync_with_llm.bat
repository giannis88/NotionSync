@echo off
setlocal enabledelayedexpansion

REM Set up logging
set "LOG_FILE=notion_sync.log"
set "TIMESTAMP=%date:~-4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TIMESTAMP=!TIMESTAMP: =0!"

echo [%TIMESTAMP%] Starting Notion Sync >> %LOG_FILE%

REM Change to script directory
cd /d %~dp0
echo [%TIMESTAMP%] Changed to directory: %CD% >> %LOG_FILE%

REM Check Python installation
python --version > nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo [%TIMESTAMP%] ERROR: Python not found >> %LOG_FILE%
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist notion_sync_env\Scripts\activate (
    echo Virtual environment not found. Creating new environment...
    echo [%TIMESTAMP%] Creating new virtual environment >> %LOG_FILE%
    python -m venv notion_sync_env
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        echo [%TIMESTAMP%] ERROR: Virtual environment creation failed >> %LOG_FILE%
        pause
        exit /b 1
    )
    
    REM Install requirements
    call notion_sync_env\Scripts\activate
    echo [%TIMESTAMP%] Installing requirements >> %LOG_FILE%
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install requirements
        echo [%TIMESTAMP%] ERROR: Requirements installation failed >> %LOG_FILE%
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo [%TIMESTAMP%] Activating virtual environment >> %LOG_FILE%
call notion_sync_env\Scripts\activate
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    echo [%TIMESTAMP%] ERROR: Virtual environment activation failed >> %LOG_FILE%
    pause
    exit /b 1
)

REM Check for .env file
if not exist .env (
    echo ERROR: .env file not found
    echo [%TIMESTAMP%] ERROR: .env file missing >> %LOG_FILE%
    pause
    exit /b 1
)

REM Run the sync scripts with error checking
echo [%TIMESTAMP%] Running auto_notion_sync.py >> %LOG_FILE%
python auto_notion_sync.py
if errorlevel 1 (
    echo ERROR: Failed to run auto_notion_sync.py
    echo [%TIMESTAMP%] ERROR: auto_notion_sync.py failed >> %LOG_FILE%
    pause
    exit /b 1
)

echo [%TIMESTAMP%] Running process_updates.py >> %LOG_FILE%
python process_updates.py
if errorlevel 1 (
    echo ERROR: Failed to run process_updates.py
    echo [%TIMESTAMP%] ERROR: process_updates.py failed >> %LOG_FILE%
    pause
    exit /b 1
)

REM Clean up old log files (keep last 5)
echo [%TIMESTAMP%] Cleaning up old log files >> %LOG_FILE%
for /f "skip=5 delims=" %%F in ('dir /b /o-d notion_sync_*.log 2^>nul') do del "%%F"

echo [%TIMESTAMP%] Successfully completed all operations >> %LOG_FILE%
echo Successfully completed all operations
pause