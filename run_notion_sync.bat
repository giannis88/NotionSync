@echo off
cd /d %~dp0
call notion_sync_env\Scripts\activate
python auto_notion_sync.py
python claude_formatter.py
pause