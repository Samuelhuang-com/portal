@echo off
title Portal - DEV Mode
echo ============================================
echo  Portal DEV Mode
echo  Backend : http://127.0.0.1:8000
echo  Frontend: http://127.0.0.1:5173
echo ============================================
echo.

:: ── Step 1：清除佔用 port 的舊程序（精確模式，不砍其他 Python）──────────────
echo [1/3] Stopping old servers on port 8000 and 5173...

for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000 " 2^>nul') do (
    if not "%%p"=="" (
        echo   Killing PID %%p (port 8000)
        taskkill /F /PID %%p >nul 2>&1
    )
)
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":5173 " 2^>nul') do (
    if not "%%p"=="" (
        echo   Killing PID %%p (port 5173)
        taskkill /F /PID %%p >nul 2>&1
    )
)

:: 等待 port 釋放
timeout /t 2 /nobreak >nul

:: ── Step 2：啟動後端 ────────────────────────────────────────────────────────
echo [2/3] Starting Backend...
start "Backend DEV" cmd /k "cd /d C:\OneDrive\_Ragic\portal\backend && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

timeout /t 2 /nobreak >nul

:: ── Step 3：啟動前端 ────────────────────────────────────────────────────────
echo [3/3] Starting Frontend...
start "Frontend DEV" cmd /k "cd /d C:\OneDrive\_Ragic\portal\frontend && npm run dev"

echo.
echo Both servers starting...
echo Frontend: http://127.0.0.1:5173
echo Backend:  http://127.0.0.1:8000
echo.
pause
