@echo off
echo Installing Notion Template Watcher Service...

REM Check for admin privileges
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Running with administrator privileges
) else (
    echo Please run this script as administrator
    pause
    exit /b 1
)

REM Set the working directory to the script's location
cd /d "%~dp0"
echo Working directory: %CD%

REM Create and activate virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate

REM Install requirements
echo Installing dependencies...
pip install -r requirements.txt

REM Install the service
echo Installing the service...
python "%CD%\install_template_service.py" install

REM Start the service
echo Starting the service...
python "%CD%\install_template_service.py" start

echo.
echo Service installation complete!
echo You can manage the service using:
echo   - python install_template_service.py start
echo   - python install_template_service.py stop
echo   - python install_template_service.py restart
echo   - python install_template_service.py remove
echo.

pause
