@echo off
echo Uninstalling Notion Template Watcher Service...

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

REM Activate virtual environment
call venv\Scripts\activate

REM Stop and remove the service
echo Stopping and removing the service...
python "%CD%\install_template_service.py" stop
python "%CD%\install_template_service.py" remove

echo.
echo Service uninstallation complete!
echo.

pause
