@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title Portal - Prod Update (New Server / C:\portal) v3

REM ==============================================================================
REM  Portal Production Update Tool - NEW SERVER
REM    Install path : C:\portal
REM    Database     : C:\Portal_Data\portal.db
REM    Service      : taskkill port 8000 + uvicorn console window (no NSSM)
REM    Local files  : backed up via "git stash push -u" (stash is kept, not dropped)
REM ==============================================================================

set "PORTAL_ROOT=C:\portal"
set "PORTAL_DATA=C:\Portal_Data"
set "PORTAL_PORT=8000"

REM ------------------------------------------------------------------------------
REM  Anti-close: relaunch in a new window, running from a copy in %TEMP%.
REM
REM  Running from %TEMP% is NOT cosmetic. cmd reads a .bat file from disk line by
REM  line while it runs. If this script sits inside %PORTAL_ROOT% and is untracked,
REM  "git stash push -u" below moves it into the stash, the file vanishes mid-run
REM  and cmd dies with "The batch file cannot be found." before git pull executes.
REM ------------------------------------------------------------------------------
REM  Relaunch when EITHER is true:
REM    a) first launch (PROD_LAUNCHED not set)  -> anti-close, open own window
REM    b) we are running from inside %PORTAL_ROOT% -> git would stash us away
REM  (b) also covers re-running the script inside the cmd /k window left over from
REM  a previous run, where PROD_LAUNCHED is already 1 and (a) alone would pass.
REM  No loop risk: after relaunch %~dp0 is %TEMP%, so (b) is false.
set "NEED_RELAUNCH="
if not "%PROD_LAUNCHED%"=="1"       set "NEED_RELAUNCH=1"
if /i "%~dp0"=="%PORTAL_ROOT%\"     set "NEED_RELAUNCH=1"

if defined NEED_RELAUNCH (
    set PROD_LAUNCHED=1
    copy /y "%~f0" "%TEMP%\portal_prod_update_run.bat" >nul
    if errorlevel 1 (
        echo [ERROR] Failed to copy this script to %%TEMP%%.
        pause
        exit /b 1
    )
    start "Portal Prod Update" cmd /k ""%TEMP%\portal_prod_update_run.bat""
    exit /b
)

if not exist "%PORTAL_ROOT%\.git" (
    echo [ERROR] %PORTAL_ROOT% not found or not a git repo!
    pause
    exit /b 1
)
cd /d "%PORTAL_ROOT%"

echo.
echo ======================================
echo  Portal - Prod Update (New Server)  v3
echo  Running from : %~f0
echo  Root : %PORTAL_ROOT%
echo  Data : %PORTAL_DATA%
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

REM == Step 1: Git Pull ==========================================================
echo [1/5] Git Pull from GitHub...
echo.

for /f %%i in ('git rev-parse HEAD 2^>nul') do set BEFORE_HASH=%%i
if "%BEFORE_HASH%"=="" set BEFORE_HASH=4b825dc642cb6eb9a060e54bf8d69288fbee4904

REM -- timestamp (used as the stash label)
for /f %%t in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set "TS=%%t"

REM -- fetch first so the pull below is a pure merge
echo [INFO] Fetching origin/main...
git fetch origin main
if errorlevel 1 (
    echo [ERROR] git fetch failed! Check network / credentials.
    pause
    exit /b 1
)

REM -- show git's real filenames instead of \346\226\260 escapes (repo-local)
git config core.quotepath false

REM ------------------------------------------------------------------------------
REM  Backup + clear anything that could block the merge.
REM
REM  "git stash" WITHOUT -u only stashes tracked-and-modified files. When upstream
REM  starts tracking a file that already exists here as a local artefact, the pull
REM  aborts with "untracked working tree files would be overwritten by merge".
REM
REM  "git stash push -u" stashes tracked modifications AND untracked files in one
REM  go. The stash IS the backup, so it is deliberately NOT dropped afterwards.
REM  Recover a file with:
REM      git checkout "stash@{0}^3" -- <path>        (untracked files live in ^3)
REM      git stash list                              (see all saved stashes)
REM ------------------------------------------------------------------------------
echo [INFO] Stashing local modifications and untracked files...
echo [INFO] The stash is the backup - it is kept, not dropped.
echo.
git stash push -u -m "prod-update %TS%"
if errorlevel 1 (
    echo [ERROR] git stash push -u failed!
    pause
    exit /b 1
)
echo.

git pull origin main
if errorlevel 1 (
    echo.
    echo [ERROR] git pull failed!
    echo [HINT]  Your files are safe in the stash: git stash list
    echo         Restore one with: git checkout "stash@{0}^^3" -- ^<path^>
    pause
    exit /b 1
)

echo.
echo ----------------------------------------
echo New commits:
git log %BEFORE_HASH%..HEAD --oneline

for /f %%i in ('git log %BEFORE_HASH%..HEAD --oneline ^| find /c /v ""') do set NEW_COMMITS=%%i
if "%NEW_COMMITS%"=="0" (
    echo   ^(no new commits^)
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

REM -- write version_info.json (PATH here has git; the backend process PATH may not)
cd /d "%PORTAL_ROOT%\backend"
py -3.12 write_version_file.py
cd /d "%PORTAL_ROOT%"

echo [OK] Code updated. Next: install backend packages [2/5]
echo.
pause

REM == Step 2: Backend packages ==================================================
echo.
echo [2/5] Installing backend packages (Python 3.12)...
cd /d "%PORTAL_ROOT%\backend"
py -3.12 -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] pip install failed!
    pause
    exit /b 1
)
echo [OK] Backend packages installed. Next: DB Index [3/5]
echo.
pause

REM == Step 3: DB Index ==========================================================
echo.
echo [3/5] Creating DB indexes...
echo [INFO] Expected DB location: %PORTAL_DATA%\portal.db
if not exist "%PORTAL_DATA%\portal.db" (
    echo [WARN] %PORTAL_DATA%\portal.db not found.
    echo [WARN] Check DATABASE_URL in %PORTAL_ROOT%\backend\.env before continuing.
    pause
)
cd /d "%PORTAL_ROOT%\backend"
py -3.12 create_indexes.py
if errorlevel 1 (
    echo [WARN] create_indexes.py returned error, please verify.
)
echo [OK] DB indexes done. Next: build frontend [4/5]
echo.
pause

REM == Step 4: Frontend build ====================================================
echo.
echo [4/5] Installing frontend packages and building...
cd /d "%PORTAL_ROOT%\frontend"

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
dir "%PORTAL_ROOT%\frontend\dist\assets\*.js" 2>nul | findstr /v "^$"

:step5

REM == Step 5: Restart uvicorn ===================================================
echo.
echo [5/5] Restarting production service (taskkill + uvicorn)...
echo.

for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":%PORTAL_PORT% " ^| findstr "LISTENING"') do (
    echo [INFO] Killing PID %%p (port %PORTAL_PORT%)...
    taskkill /PID %%p /F >nul 2>&1
)

timeout /t 2 /nobreak >nul

echo [INFO] Starting uvicorn...
start "Portal Backend" cmd /k "cd /d %PORTAL_ROOT%\backend && py -3.12 -m uvicorn app.main:app --host 0.0.0.0 --port %PORTAL_PORT% --workers 1"
echo [OK] uvicorn started in a new window (do not close it)

echo.
echo ======================================
echo  Update complete!
echo.
echo  Latest 3 commits:
git -C "%PORTAL_ROOT%" log --oneline -3
echo.
echo  Local files before this update are saved in stash: prod-update %TS%
echo    list    : git stash list
echo    inspect : git show "stash@{0}^^3" --stat
echo    restore : git checkout "stash@{0}^^3" -- ^<path^>
echo.
echo  Frontend: http://[server-ip]:%PORTAL_PORT%
echo ======================================
echo.
pause
endlocal
