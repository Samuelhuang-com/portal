@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title Portal - Auto Update (New Server / C:\portal)

REM ==============================================================================
REM  Portal AUTOMATIC Update Tool - NEW SERVER (C:\portal)
REM
REM  Designed to be launched by Windows Task Scheduler every N minutes.
REM  NON-INTERACTIVE: no "pause", no prompts, never waits for a human.
REM
REM  It does NOTHING at all unless origin/main actually has new commits, so a
REM  10-minute polling interval costs one "git fetch" and nothing else.
REM
REM  Manual / first-time deployment still uses prod-update-newserver.bat.
REM  That script is untouched by this one.
REM
REM  Setup instructions: docs/AUTO_UPDATE.md
REM ==============================================================================

set "PORTAL_ROOT=C:\portal"
set "PORTAL_DATA=C:\Portal_Data"
set "PORTAL_PORT=8000"
set "LOG_DIR=%PORTAL_DATA%\update-logs"
set "LOCK_FILE=%PORTAL_DATA%\auto-update.running"
set "FAIL_FLAG=%PORTAL_DATA%\auto-update-FAILED.txt"
set "SYNC_OWNER=%PORTAL_DATA%\.sync.lock.owner"
set "SELF_COPY=%TEMP%\portal_auto_update_run.bat"
set "DIST_BAK=%PORTAL_DATA%\frontend-dist.bak"
set "LOG_KEEP_DAYS=30"
set "STALE_LOCK_MINUTES=90"

REM  Never let git open a credential prompt. In a scheduled run nobody is there
REM  to answer it, and the task would hang forever holding the lock.
set "GIT_TERMINAL_PROMPT=0"
set "GCM_INTERACTIVE=never"

REM ------------------------------------------------------------------------------
REM  Run from a copy in %TEMP%, exactly like prod-update-newserver.bat does.
REM  cmd reads a .bat from disk line by line WHILE it runs; if this file is ever
REM  locally modified, "git stash push -u" below would move it into the stash and
REM  cmd would die mid-run with "The batch file cannot be found."
REM
REM  The whole relaunch is ONE logical line on purpose: cmd buffers a full line
REM  before executing it, so nothing is read from the original file afterwards.
REM
REM  The "already relaunched" test is an environment flag, NOT a path comparison.
REM  %TEMP% is often the 8.3 short form (C:\Users\SAM~1\...) while %~f0 always
REM  expands to the long path, so comparing them can never match and the script
REM  would relaunch itself forever. "call" keeps the same environment, so the
REM  child sees the flag.
REM ------------------------------------------------------------------------------
if "%PORTAL_AUTO_CHILD%"=="1" goto :main

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1
call :today_stamp
copy /y "%~f0" "%SELF_COPY%" >nul
if errorlevel 1 (
    echo [ERROR] Failed to copy this script to %%TEMP%%.
    exit /b 1
)
set "PORTAL_AUTO_CHILD=1"
call "%SELF_COPY%" >> "%LOG_DIR%\auto-update-!TODAY!.log" 2>&1 & exit /b !errorlevel!


REM ==============================================================================
REM  MAIN
REM ==============================================================================
:main
set "RC=0"
set "STAGE=start"

echo.
echo ==================================================================
echo  Portal Auto Update   %DATE% %TIME%
echo  Root : %PORTAL_ROOT%    Data : %PORTAL_DATA%
echo ==================================================================

if not exist "%PORTAL_ROOT%\.git" (
    echo [ERROR] %PORTAL_ROOT% is not a git repository.
    set "RC=1"
    set "STAGE=preflight"
    goto :fail_no_lock
)

py -3.12 --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.12 not found.
    set "RC=1"
    set "STAGE=preflight"
    goto :fail_no_lock
)

REM -- Step 0a: only one run at a time -------------------------------------------
if exist "%LOCK_FILE%" (
    call :lock_state
    if /i "!LOCK_STATE!"=="LIVE" (
        echo [SKIP] A previous auto-update run is still going. Nothing done.
        exit /b 0
    )
    echo [WARN] Lock file older than %STALE_LOCK_MINUTES% min - treating as stale and removing.
    del /f /q "%LOCK_FILE%" >nul 2>&1
)
echo %DATE% %TIME% > "%LOCK_FILE%"

REM -- Step 0b: never interrupt a running Ragic sync ------------------------------
REM  app/core/sync_lock.py writes "<host>\t<pid>\t<module>\t<started>" into
REM  .sync.lock.owner while a sync holds the cross-process lock. The owner file is
REM  best-effort (a hard-killed process leaves it behind), so the pid is checked.
call :sync_busy
if /i "!SYNC_BUSY!"=="1" (
    echo [SKIP] A Ragic sync is running right now - deferring to the next round.
    goto :finish
)

REM -- Step 1: is there anything new at all? --------------------------------------
cd /d "%PORTAL_ROOT%"
set "STAGE=fetch"

if exist .git\index.lock (
    echo [WARN] Removing stale .git\index.lock
    del /f .git\index.lock >nul 2>&1
)

REM  quotepath off must run on its own line. Inside a for /f back-quote block cmd
REM  treats "=" as an argument separator and "git -c core.quotepath=false" breaks.
git config core.quotepath false

git fetch origin main
if errorlevel 1 (
    echo [ERROR] git fetch failed - network or credentials.
    set "RC=1"
    goto :fail
)

set "NEW_COUNT=0"
for /f %%c in ('git rev-list --count HEAD..origin/main') do set "NEW_COUNT=%%c"
if "!NEW_COUNT!"=="0" (
    echo [OK] Already up to date - no new commits. Nothing to do.
    goto :finish
)
echo [INFO] !NEW_COUNT! new commit^(s^) on origin/main:
git log HEAD..origin/main --oneline

for /f %%i in ('git rev-parse HEAD') do set "BEFORE_HASH=%%i"

REM -- Step 2: what kind of update is this? ---------------------------------------
REM  Pathspec-scoped diffs return output only when that path changed. This avoids
REM  findstr entirely - findstr stops matching as soon as it hits UTF-8 content,
REM  and this repo is full of Chinese filenames.
set "NEED_PIP="
set "NEED_NPM_INSTALL="
set "NEED_BUILD="
for /f "delims=" %%f in ('git diff --name-only HEAD origin/main -- backend/requirements.txt') do set "NEED_PIP=1"
for /f "delims=" %%f in ('git diff --name-only HEAD origin/main -- frontend/package.json frontend/package-lock.json') do set "NEED_NPM_INSTALL=1"
for /f "delims=" %%f in ('git diff --name-only HEAD origin/main -- frontend') do set "NEED_BUILD=1"

REM -- Step 3: back up local changes, then fast-forward ---------------------------
set "STAGE=pull"
call :today_time_stamp

set "DIRTY="
for /f "delims=" %%s in ('git status --porcelain') do set "DIRTY=1"
if defined DIRTY (
    echo [INFO] Local modifications found - stashing them as a backup.
    git stash push -u -m "auto-update !TS!"
    if errorlevel 1 (
        echo [ERROR] git stash push -u failed.
        set "RC=1"
        goto :fail
    )
) else (
    echo [INFO] Working tree clean - no stash needed.
)

REM  --ff-only, not a merge. If this server ever grows its own commits the update
REM  must stop and say so, not silently create a merge commit nobody reviewed.
git pull --ff-only origin main
if errorlevel 1 (
    echo [ERROR] git pull --ff-only failed. The server may have diverged from origin/main.
    echo [HINT]  Local files are safe in the stash: git stash list
    set "RC=1"
    goto :fail
)
echo [OK] Updated to:
git log --oneline -1

REM -- Step 4: version file + backend packages ------------------------------------
set "STAGE=backend"
cd /d "%PORTAL_ROOT%\backend"
py -3.12 write_version_file.py
if errorlevel 1 echo [WARN] write_version_file.py failed - /api/v1/version may show a stale commit.

if defined NEED_PIP (
    echo [INFO] requirements.txt changed - installing backend packages.
    py -3.12 -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] pip install failed.
        set "RC=1"
        goto :fail
    )
) else (
    echo [SKIP] requirements.txt unchanged.
)

if not exist "%PORTAL_DATA%\portal.db" (
    echo [WARN] %PORTAL_DATA%\portal.db not found - check DATABASE_URL in backend\.env
)

REM -- Step 4b: Alembic migration (unattended) ------------------------------------
REM    Unlike prod-update.bat this runs with --yes: nobody is watching, so it must
REM    never wait for input. The safety comes from alembic_deploy.py itself:
REM      exit 0 = up to date, or applied successfully  -> continue
REM      exit 2 = needs a human (usually: this machine was never stamped)
REM               -> ABORT THE WHOLE ROUND and do NOT restart the service.
REM               Leaving the server on the old code is the safe outcome; a
REM               half-migrated DB behind new code is not.
REM      exit 1 = migration failed -> same, abort.
REM    First-time setup on a machine:
REM      cd C:\portal\backend
REM      py -3.12 scripts\check_schema_drift.py
REM      py -3.12 scripts\alembic_stamp_baseline.py
set "STAGE=migrate"
echo [INFO] Checking database migrations...
py -3.12 scripts\alembic_deploy.py --yes
set "MIGRATE_RC=!errorlevel!"
if not "!MIGRATE_RC!"=="0" (
    echo [ERROR] Migration step returned !MIGRATE_RC! - aborting this round.
    if "!MIGRATE_RC!"=="2" (
        echo [HINT]  This machine has probably never been stamped. Run once, by hand:
        echo [HINT]      cd %PORTAL_ROOT%\backend
        echo [HINT]      py -3.12 scripts\check_schema_drift.py
        echo [HINT]      py -3.12 scripts\alembic_stamp_baseline.py
    )
    echo [INFO]  Service NOT restarted - still running the previous version.
    set "RC=1"
    goto :fail
)

set "STAGE=backend"
py -3.12 create_indexes.py
if errorlevel 1 echo [WARN] create_indexes.py returned an error - please verify.

REM -- Step 5: frontend ------------------------------------------------------------
set "STAGE=frontend"
cd /d "%PORTAL_ROOT%\frontend"

if not exist package.json (
    echo [SKIP] No package.json - skipping frontend.
    goto :restart
)
if not defined NEED_BUILD (
    echo [SKIP] Nothing under frontend/ changed - keeping the existing dist.
    goto :restart
)

if defined NEED_NPM_INSTALL (
    echo [INFO] package.json / lockfile changed - running npm install.
    call npm install
    if errorlevel 1 (
        echo [ERROR] npm install failed.
        set "RC=1"
        goto :fail
    )
) else (
    echo [SKIP] package.json unchanged - reusing node_modules.
)

REM  Keep the currently-served dist. A failed build must never leave the site
REM  with a half-written bundle - users are online while this runs.
REM
REM  The backup lives OUTSIDE the repo on purpose. ".gitignore" ignores "dist/"
REM  but not "dist.bak/", so a copy left inside frontend/ would be untracked and
REM  the next run's "git stash push -u" would sweep a whole build into the stash.
if exist dist (
    echo [INFO] Backing up current dist to %DIST_BAK% ...
    robocopy dist "%DIST_BAK%" /MIR /NFL /NDL /NJH /NJS /NP >nul
)

call npm run build
if errorlevel 1 (
    echo [ERROR] npm run build failed - most likely a TypeScript error.
    if exist "%DIST_BAK%" (
        echo [INFO] Restoring the previous dist - the site keeps serving the old build.
        robocopy "%DIST_BAK%" dist /MIR /NFL /NDL /NJH /NJS /NP >nul
    )
    set "RC=1"
    goto :fail
)
echo [OK] Frontend build succeeded.
if exist "%DIST_BAK%" rmdir /s /q "%DIST_BAK%" >nul 2>&1

REM -- Step 6: restart uvicorn -----------------------------------------------------
:restart
set "STAGE=restart"
echo [INFO] Restarting backend on port %PORTAL_PORT%...

REM  Re-check the sync lock: the build above can take minutes and a scheduled
REM  sync may have started in the meantime.
call :sync_busy
if /i "!SYNC_BUSY!"=="1" (
    echo [WARN] A Ragic sync started during the build. Code is updated but the
    echo [WARN] backend was NOT restarted. The next round will restart it.
    goto :finish
)

for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":%PORTAL_PORT% " ^| findstr "LISTENING"') do (
    echo [INFO] Stopping PID %%p
    taskkill /PID %%p /F >nul 2>&1
)
timeout /t 3 /nobreak >nul

start "Portal Backend" cmd /k "cd /d %PORTAL_ROOT%\backend && py -3.12 -m uvicorn app.main:app --host 0.0.0.0 --port %PORTAL_PORT% --workers 1"
echo [INFO] uvicorn window started - do not close it.

call :health_check
if /i "!HEALTH!"=="OK" (
    echo [OK] Backend is listening on port %PORTAL_PORT% again.
) else (
    echo [ERROR] Backend did not come back up within the health-check window.
    echo [HINT]  Check the "Portal Backend" console window for a traceback.
    set "RC=1"
    goto :fail
)

goto :finish


REM ==============================================================================
REM  EXIT PATHS
REM ==============================================================================
:fail
echo [FAILED] stage=%STAGE%
> "%FAIL_FLAG%" echo Portal auto-update FAILED at stage "%STAGE%" on %DATE% %TIME%
>> "%FAIL_FLAG%" echo See %LOG_DIR% for the full log.
goto :finish

:fail_no_lock
echo [FAILED] stage=%STAGE%
> "%FAIL_FLAG%" echo Portal auto-update FAILED at stage "%STAGE%" on %DATE% %TIME%
exit /b %RC%

:finish
if "%RC%"=="0" if exist "%FAIL_FLAG%" del /f /q "%FAIL_FLAG%" >nul 2>&1
del /f /q "%LOCK_FILE%" >nul 2>&1
forfiles /P "%LOG_DIR%" /M auto-update-*.log /D -%LOG_KEEP_DAYS% /C "cmd /c del @path" >nul 2>&1
echo [DONE] rc=%RC%   %DATE% %TIME%
exit /b %RC%


REM ==============================================================================
REM  SUBROUTINES
REM
REM  Every PowerShell call lives in a subroutine on purpose. Inside an if(...)
REM  block cmd counts the parentheses in the quoted PowerShell command as part of
REM  the block and mis-parses it; at subroutine top level that cannot happen.
REM ==============================================================================

:today_stamp
set "TODAY=unknown"
for /f %%t in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd"') do set "TODAY=%%t"
goto :eof

:today_time_stamp
set "TS=unknown"
for /f %%t in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set "TS=%%t"
goto :eof

REM  NOTE: none of the PowerShell one-liners below contain a "=" character, on
REM  purpose. An unquoted "=" inside a for /f back-quoted command is what broke
REM  "git -c core.quotepath=false" (see prod-update-newserver.bat, pitfall #1).
REM  Keeping them assignment-free removes the question entirely.

:lock_state
REM  LIVE = a real run is in progress, STALE = leftover from a killed run
set "LOCK_STATE=LIVE"
for /f %%s in ('powershell -NoProfile -Command "if(((Get-Date)-(Get-Item $env:LOCK_FILE).LastWriteTime).TotalMinutes -gt [double]$env:STALE_LOCK_MINUTES){'STALE'}else{'LIVE'}"') do set "LOCK_STATE=%%s"
goto :eof

:sync_busy
REM  1 = a sync process is alive and holding the cross-process lock.
REM  No regex here: "^" is cmd's escape character and would be eaten before
REM  PowerShell ever sees it. "-as [int]" does the same job safely, and the
REM  try/catch covers a malformed or truncated owner file.
set "SYNC_BUSY=0"
if not exist "%SYNC_OWNER%" goto :eof
for /f %%b in ('powershell -NoProfile -Command "try{if(Get-Process -Id (((Get-Content $env:SYNC_OWNER -Raw) -split [char]9)[1] -as [int]) -ErrorAction SilentlyContinue){'1'}else{'0'}}catch{'0'}"') do set "SYNC_BUSY=%%b"
if "!SYNC_BUSY!"=="1" (
    echo [INFO] Sync lock owner:
    type "%SYNC_OWNER%"
    echo.
)
goto :eof

:port_open
REM  errorlevel 0 when something is LISTENING on PORTAL_PORT.
REM  netstat output is pure ASCII, so findstr is safe here - unlike the
REM  file-path comparisons elsewhere, which is why those use git pathspecs.
netstat -ano | findstr ":%PORTAL_PORT% " | findstr "LISTENING" >nul 2>&1
goto :eof

:health_check
REM  uvicorn imports the app before it binds, so "port is listening again"
REM  is a good enough readiness signal and needs no curl (not present on
REM  older Windows Server builds).
set "HEALTH=FAIL"
for /l %%i in (1,1,30) do (
    if not "!HEALTH!"=="OK" (
        call :port_open
        if not errorlevel 1 (
            set "HEALTH=OK"
        ) else (
            timeout /t 2 /nobreak >nul
        )
    )
)
goto :eof
