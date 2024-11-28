@echo off
echo Setting up Notion Dashboard Environment...

REM Display current directory
echo Current directory: %CD%
echo Checking for requirements.txt...
if exist "requirements.txt" (
    echo Found requirements.txt
) else (
    echo ERROR: requirements.txt not found in %CD%
    pause
    exit /b 1
)

REM Check for .env file
if not exist ".env" (
    echo Creating .env file from template...
    copy .env.example .env
    echo Please edit .env file with your Notion API credentials before continuing
    notepad .env
    pause
    exit /b 1
)

REM Create user-specific virtual environment path
set VENV_PATH=%USERPROFILE%\notion_sync_env

REM Check if virtual environment exists
IF NOT EXIST "%VENV_PATH%" (
    echo Creating virtual environment in %VENV_PATH%...
    python -m venv "%VENV_PATH%"
)

REM Activate virtual environment
echo Activating virtual environment...
call "%VENV_PATH%\Scripts\activate.bat"

REM Check if activation was successful
IF %ERRORLEVEL% NEQ 0 (
    echo Failed to activate virtual environment
    echo Please run this script as administrator
    pause
    exit /b 1
)

REM Install requirements
echo Installing dependencies from %CD%\requirements.txt...
pip install -r "%CD%\requirements.txt"

REM Check if installation was successful
IF %ERRORLEVEL% NEQ 0 (
    echo Failed to install dependencies
    echo Check if requirements.txt exists and is accessible
    pause
    exit /b 1
)

REM Create necessary directories
echo Creating necessary directories...
if not exist "data" mkdir data
if not exist "dashboard" mkdir dashboard
if not exist "templates" mkdir templates

REM Run the dashboard processor
echo Running dashboard processor...
python template_populator.py

IF %ERRORLEVEL% NEQ 0 (
    echo Failed to run template populator
    pause
    exit /b 1
)

echo Creating Notion pages...
python notion_page_creator.py

IF %ERRORLEVEL% NEQ 0 (
    echo Failed to create Notion pages
    pause
    exit /b 1
)

python process_dashboard.py

IF %ERRORLEVEL% NEQ 0 (
    echo Failed to run dashboard processor
    pause
    exit /b 1
)

echo Process complete!
pause
