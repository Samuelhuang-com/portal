@echo off
title Portal - PROD Preview Mode
echo ============================================
echo  Portal PROD Preview Mode
echo  Backend : http://127.0.0.1:8000
echo  Frontend: http://127.0.0.1:4173
echo ============================================
echo.

start "Backend PROD" cmd /k "cd /d C:\OneDrive\_Ragic\portal\backend && uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo [1/2] Building frontend...
cd /d C:\OneDrive\_Ragic\portal\frontend
call npm run build
if %errorlevel% neq 0 (
    echo Build failed. Check errors above.
    pause
    exit /b 1
)

echo [2/2] Starting preview server...
start "Frontend PROD" cmd /k "cd /d C:\OneDrive\_Ragic\portal\frontend && npx vite preview --host 127.0.0.1"

echo.
echo Build done. Preview server started.
echo Frontend: http://127.0.0.1:4173
echo Backend:  http://127.0.0.1:8000
echo.
pause
