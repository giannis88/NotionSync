@echo off
echo Starting Dashboard Analysis...
call notion_sync_env\Scripts\activate.bat
python template_populator.py
python process_dashboard.py
pause
