@echo off
title Portal - DEV Mode
echo ============================================
echo  Portal DEV Mode
echo  Backend : http://127.0.0.1:8000
echo  Frontend: http://127.0.0.1:5173
echo ============================================
echo.

start "Backend DEV" cmd /k "cd /d C:\OneDrive\_Ragic\portal\backend && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

timeout /t 2 /nobreak >nul

start "Frontend DEV" cmd /k "cd /d C:\OneDrive\_Ragic\portal\frontend && npm run dev"

echo Both servers starting...
echo Frontend: http://127.0.0.1:5173
echo Backend:  http://127.0.0.1:8000
echo.
pause
