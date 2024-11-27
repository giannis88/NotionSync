@echo off
cd /d %~dp0

REM Check if virtual environment exists
if not exist notion_sync_env\Scripts\activate (
    echo Virtual environment not found. Please set up the environment first.
    pause
    exit /b 1
)

REM Activate virtual environment and run scripts
call notion_sync_env\Scripts\activate

REM Run the sync scripts with error checking
python auto_notion_sync.py
if errorlevel 1 (
    echo Error in auto_notion_sync.py
    pause
    exit /b 1
)

python process_updates.py
if errorlevel 1 (
    echo Error in process_updates.py
    pause
    exit /b 1
)

echo Successfully completed all operations
pause 