@echo off
chcp 65001 >nul
title Portal - Prod Update v4

REM -- anti-close: open new window
if not "%PROD_LAUNCHED%"=="1" (
    set PROD_LAUNCHED=1
    start "Portal Prod Update" cmd /k ""%~f0""
    exit /b
)

cd /d D:\portal

echo.
echo ======================================
echo  Portal - Prod Update Tool v4
echo ======================================
echo.

REM -- check Python 3.12
py -3.12 --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.12 not found!
    pause
    exit /b 1
)
echo [OK] Python 3.12 OK

REM -- clear stale index.lock
if exist .git\index.lock (
    echo [WARN] Removing stale .git\index.lock...
    del /f .git\index.lock
    echo [OK] index.lock removed
)
echo.

REM ── Step 1: Git Pull ──────────────────────────────────────────────────────────
echo [1/5] Git Pull from GitHub...
echo.

for /f %%i in ('git rev-parse HEAD 2^>nul') do set BEFORE_HASH=%%i
if "%BEFORE_HASH%"=="" set BEFORE_HASH=4b825dc642cb6eb9a060e54bf8d69288fbee4904

git stash

if exist run_sync_tool.bat (
    del /f run_sync_tool.bat
    echo [INFO] Removed untracked run_sync_tool.bat
)

git pull origin main
if errorlevel 1 (
    echo [ERROR] git pull failed!
    pause
    exit /b 1
)

git stash drop >nul 2>&1

echo.
echo ----------------------------------------
echo New commits:
git log %BEFORE_HASH%..HEAD --oneline

for /f %%i in ('git log %BEFORE_HASH%..HEAD --oneline ^| find /c /v ""') do set NEW_COMMITS=%%i
if "%NEW_COMMITS%"=="0" (
    echo   (no new commits)
) else (
    echo.
    echo Changed files:
    git diff --name-status %BEFORE_HASH% HEAD
)
echo.
echo Latest commit:
git log --oneline -1
echo ----------------------------------------
echo.

REM -- write version_info.json (PATH here has git; PortalBackend NSSM service PATH does not)
cd /d D:\portal\backend
py -3.12 write_version_file.py
cd /d D:\portal

echo [OK] Code updated. Next: install backend packages [2/5]
echo.
pause

REM ── Step 2: Backend packages ──────────────────────────────────────────────────
echo.
echo [2/5] Installing backend packages (Python 3.12)...
cd /d D:\portal\backend
py -3.12 -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] pip install failed!
    pause
    exit /b 1
)
echo [OK] Backend packages installed. Next: DB Index [3/5]
echo.
pause

REM ── Step 3: DB Index ──────────────────────────────────────────────────────────
echo.
echo [3/5] Creating DB indexes...
cd /d D:\portal\backend
py -3.12 create_indexes.py
if errorlevel 1 (
    echo [WARN] create_indexes.py returned error, please verify.
)
echo [OK] DB indexes done. Next: build frontend [4/5]
echo.
pause

REM ── Step 4: Frontend build ────────────────────────────────────────────────────
echo.
echo [4/5] Installing frontend packages and building...
cd /d D:\portal\frontend

if not exist package.json (
    echo [SKIP] package.json not found, skipping frontend build.
    goto step5
)

npm install
if errorlevel 1 (
    echo [ERROR] npm install failed!
    pause
    exit /b 1
)

npm run build
if errorlevel 1 (
    echo.
    echo [ERROR] npm run build failed! Check TypeScript errors above.
    echo [HINT]  Fix the TS errors and re-run this tool.
    pause
    exit /b 1
)

echo.
echo [OK] Frontend build successful. dist updated:
dir D:\portal\frontend\dist\assets\*.js 2>nul | findstr /v "^$"

:step5

REM ── Step 5: Restart uvicorn ───────────────────────────────────────────────────
echo.
echo [5/5] Restarting production service...
echo.

REM -- try NSSM service first
sc query PortalBackend >nul 2>&1
if not errorlevel 1 (
    echo [NSSM] Found PortalBackend service, restarting...
    net stop PortalBackend
    net start PortalBackend
    echo [OK] PortalBackend service restarted
    goto done
)

REM -- fallback: taskkill port 8000 + restart
echo [INFO] No NSSM service found, using taskkill...

for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    echo [INFO] Killing PID %%p (port 8000)...
    taskkill /PID %%p /F >nul 2>&1
)

timeout /t 2 /nobreak >nul

echo [INFO] Starting uvicorn...
start "Portal Backend" cmd /k "cd /d D:\portal\backend && py -3.12 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"
echo [OK] uvicorn started in new window

:done
echo.
echo ======================================
echo  Update complete!
echo.
echo  Latest 3 commits:
git -C D:\portal log --oneline -3
echo.
echo  Frontend: http://[server-ip]:8000
echo ======================================
echo.
pause
