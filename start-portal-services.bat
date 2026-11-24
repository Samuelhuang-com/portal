@echo off
cd /d "%~dp0"

start "Portal Console" py -3.11 "%~dp0portal_console.py"

REM Wait 30 seconds before starting Sync Tool
timeout /t 30 /nobreak >nul

start "Sync Tool" py -3.11 "%~dp0sync_tool.py"