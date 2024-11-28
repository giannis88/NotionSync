@echo off
cd /d %~dp0

REM Run Notion sync
call notion_sync_env\Scripts\activate
python auto_notion_sync.py

REM Open the React app (adjust the command based on your setup)
npm run dev