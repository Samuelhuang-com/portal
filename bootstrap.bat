@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ===========================================================================
REM  Portal - Bootstrap: bare Windows machine  ->  running production server
REM
REM  IMPORTANT: This file is intentionally ASCII-ONLY.
REM  cmd.exe reads a .bat using the system OEM codepage (950/Big5 on a
REM  Traditional Chinese Windows), NOT UTF-8. A UTF-8 .bat containing Chinese
REM  gets shredded into garbage that cmd then tries to run as commands.
REM  "chcp 65001" above does NOT fix that - by the time it runs the file has
REM  already been misread. It is here for a different reason: the Python
REM  scripts we call (init_db.py etc.) print emoji, which a cp950 console
REM  cannot encode. PYTHONIOENCODING below is the real guard; chcp helps too.
REM  Chinese instructions are in: docs/DEPLOY_BOOTSTRAP.md
REM
REM  USAGE  (right-click -> Run as administrator):
REM      bootstrap.bat "E:\backup\.env"
REM      bootstrap.bat                 (will prompt for the .env path)
REM
REM  IDEMPOTENT: safe to re-run. Every step detects "already done" and skips.
REM  The source .env is validated BEFORE anything is overwritten.
REM ===========================================================================

REM ---------------------------------------------------------------------------
REM  Settings - edit these if the target layout differs
REM ---------------------------------------------------------------------------
set "PORTAL_DIR=D:\portal"
set "DATA_DIR=C:\Portal_Data"
set "REPO_URL=https://github.com/Samuelhuang-com/portal.git"
set "PORT=8000"
set "PYTAG=-3.12"
set "SVCNAME=PortalBackend"
set "WORKERS=1"

REM  Python writes its stdout using the console codepage unless told otherwise.
REM  init_db.py prints emoji; on a cp950 console that is an instant
REM  UnicodeEncodeError and a non-zero exit code. Do not remove this.
set "PYTHONIOENCODING=utf-8"

set "ENVSRC=%~1"

echo.
echo =========================================================
echo   Portal Bootstrap
echo   Target : %PORTAL_DIR%
echo   Data   : %DATA_DIR%
echo   Service: %SVCNAME%  (port %PORT%, workers %WORKERS%)
echo =========================================================
echo.

REM ---------------------------------------------------------------------------
REM  [1/10] Administrator check
REM ---------------------------------------------------------------------------
echo [1/10] Checking administrator rights...
net session >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Administrator rights required.
    echo         Right-click this file - Run as administrator.
    goto fail
)
echo [OK] Running as administrator
echo.

REM ---------------------------------------------------------------------------
REM  [2/10] Locate and VALIDATE the source .env - before touching anything
REM ---------------------------------------------------------------------------
echo [2/10] Validating the source .env...
if "%ENVSRC%"=="" (
    echo   No path given on the command line.
    set /p "ENVSRC=  Full path to the existing .env file: "
)
REM  Explorer's "Copy as path" includes quotes; %~1 strips them, set /p does not.
set "ENVSRC=!ENVSRC:"=!"
if "!ENVSRC!"=="" (
    echo [ERROR] No .env source path supplied.
    echo         Usage: bootstrap.bat "E:\backup\.env"
    goto fail
)
if not exist "!ENVSRC!" (
    echo [ERROR] .env not found: !ENVSRC!
    goto fail
)

set "ENVCHK=!ENVSRC!"
set "ENVBAD="
call :needkey SECRET_KEY
call :needkey RAGIC_API_KEY
call :needkey DATABASE_URL
call :needkey CYCLE_PURCHASE_DATABASE_URL
call :needkey CORS_ORIGINS
call :needenv

if not "!ENVBAD!"=="" (
    echo.
    echo [ERROR] Source .env has missing or empty values for:!ENVBAD!
    echo         File: !ENVSRC!
    echo.
    echo   CYCLE_PURCHASE_DATABASE_URL is the one that historically got left out.
    echo   When it is absent the backend silently falls back to a relative path,
    echo   the migration scripts write to a DIFFERENT file, and every symptom
    echo   points somewhere else. See CHANGELOG [1.90.29].
    echo.
    echo   Fix the SOURCE file above, then re-run. Nothing has been changed yet.
    goto fail
)
findstr /r /c:"^ *SECRET_KEY *=.*change-me" "!ENVSRC!" >nul 2>&1
if not errorlevel 1 (
    echo [ERROR] SECRET_KEY in the source .env is still the placeholder value.
    echo         Generate one:  py %PYTAG% -c "import secrets;print(secrets.token_hex(32))"
    goto fail
)
echo [OK] Source .env validated: !ENVSRC!
echo      DATABASE_URL in use:
findstr /r /c:"^ *DATABASE_URL *=" "!ENVSRC!"
echo.

REM ---------------------------------------------------------------------------
REM  [3/10] winget availability
REM ---------------------------------------------------------------------------
echo [3/10] Checking winget...
where winget >nul 2>&1
if errorlevel 1 (
    echo [ERROR] winget not found.
    echo         winget ships with Windows 10 1809+ / Windows 11 / Server 2022+.
    echo         On older Windows install these four manually, then re-run:
    echo           Git         https://git-scm.com/download/win
    echo           Python 3.12 https://www.python.org/downloads/
    echo           Node.js LTS https://nodejs.org/
    echo           NSSM        https://nssm.cc/download  ^(nssm.exe into System32^)
    goto fail
)
echo [OK] winget available
echo.

REM ---------------------------------------------------------------------------
REM  [4/10] Install toolchain
REM
REM  --scope machine matters: NSSM runs the service as LocalSystem, which
REM  cannot see a per-user Python under C:\Users\...\AppData.
REM ---------------------------------------------------------------------------
echo [4/10] Installing toolchain (already-present items are skipped)...

where git >nul 2>&1
if errorlevel 1 (
    echo   Installing Git...
    winget install -e --id Git.Git --scope machine --accept-source-agreements --accept-package-agreements --silent
) else (
    echo   [skip] Git already installed
)

py %PYTAG% --version >nul 2>&1
if errorlevel 1 (
    echo   Installing Python 3.12...
    winget install -e --id Python.Python.3.12 --scope machine --accept-source-agreements --accept-package-agreements --silent
) else (
    echo   [skip] Python 3.12 already installed
)

where node >nul 2>&1
if errorlevel 1 (
    echo   Installing Node.js LTS...
    winget install -e --id OpenJS.NodeJS.LTS --scope machine --accept-source-agreements --accept-package-agreements --silent
) else (
    echo   [skip] Node.js already installed
)

where nssm >nul 2>&1
if not errorlevel 1 (
    echo   [skip] NSSM already installed
) else (
    call :install_nssm
)
echo.

REM ---------------------------------------------------------------------------
REM  [5/10] Refresh PATH, then verify every tool is actually callable
REM ---------------------------------------------------------------------------
echo [5/10] Refreshing PATH for this session...
set "MPATH="
set "UPATH="
for /f "usebackq tokens=2,*" %%A in (`reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul ^| find "REG_"`) do set "MPATH=%%B"
for /f "usebackq tokens=2,*" %%A in (`reg query "HKCU\Environment" /v Path 2^>nul ^| find "REG_"`) do set "UPATH=%%B"
if defined MPATH set "PATH=%MPATH%;%UPATH%"
call set "PATH=%PATH%"

set "MISSING="
where git >nul 2>&1  || set "MISSING=!MISSING! git"
where node >nul 2>&1 || set "MISSING=!MISSING! node"
where npm >nul 2>&1  || set "MISSING=!MISSING! npm"
where nssm >nul 2>&1 || set "MISSING=!MISSING! nssm"
py %PYTAG% --version >nul 2>&1 || set "MISSING=!MISSING! python3.12"

if not "!MISSING!"=="" (
    echo.
    echo [ACTION NEEDED] Not callable yet:!MISSING!
    echo.
    echo   Most likely cause: a new PATH only reaches a console started AFTER
    echo   the install.
    echo     1. Close this window.
    echo     2. Open a NEW console as administrator.
    echo     3. Run this script again - finished steps are skipped.
    echo.
    echo   If it still fails after a fresh console, the winget install itself
    echo   failed. Check by running, for example:
    echo       winget install -e --id Python.Python.3.12 --scope machine
    echo.
    goto fail
)
echo [OK] git / python3.12 / node / npm / nssm all callable
echo.

REM ---------------------------------------------------------------------------
REM  [6/10] Source code
REM ---------------------------------------------------------------------------
echo [6/10] Fetching source code...
if not exist "%DATA_DIR%" mkdir "%DATA_DIR%"

if exist "%PORTAL_DIR%\.git" (
    echo   [skip] %PORTAL_DIR% is already a git repo - syncing to origin/main
    pushd "%PORTAL_DIR%"
    git fetch origin
    if errorlevel 1 (
        echo [ERROR] git fetch failed - refusing to deploy a possibly stale tree.
        popd
        goto fail
    )
    git reset --hard origin/main
    if errorlevel 1 (
        echo [ERROR] git reset --hard failed.
        popd
        goto fail
    )
    popd
) else (
    if exist "%PORTAL_DIR%" (
        echo [ERROR] %PORTAL_DIR% exists but is not a git repo.
        echo         Move it aside first, then re-run:
        echo             move %PORTAL_DIR% %PORTAL_DIR%_old
        goto fail
    )
    git clone "%REPO_URL%" "%PORTAL_DIR%"
    if errorlevel 1 (
        echo [ERROR] git clone failed.
        echo         If the repo is private this machine needs credentials first.
        goto fail
    )
)
if not exist "%PORTAL_DIR%\backend\app\main.py" (
    echo [ERROR] %PORTAL_DIR%\backend\app\main.py missing - clone looks incomplete.
    goto fail
)
echo [OK] Source ready at %PORTAL_DIR%
echo.

REM ---------------------------------------------------------------------------
REM  [7/10] Install the .env  (already validated in step 2)
REM ---------------------------------------------------------------------------
echo [7/10] Installing backend\.env ...
call :backup_env
copy /y "!ENVSRC!" "%PORTAL_DIR%\backend\.env" >nul
if errorlevel 1 (
    echo [ERROR] Could not copy the .env into place.
    goto fail
)
echo [OK] .env installed
echo.

REM ---------------------------------------------------------------------------
REM  [8/10] Backend
REM ---------------------------------------------------------------------------
echo [8/10] Backend: packages, database, indexes...
pushd "%PORTAL_DIR%\backend"

py %PYTAG% -m pip install --upgrade pip
py %PYTAG% -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] pip install failed.
    popd
    goto fail
)
echo   [OK] Python packages installed

REM  init_db.py is itself idempotent (create_all + check-then-insert), so it is
REM  safe to run every time. Do NOT gate this on backend\portal.db existing -
REM  the DB lives wherever DATABASE_URL points, normally %DATA_DIR%.
py %PYTAG% init_db.py
if errorlevel 1 (
    echo [ERROR] init_db.py failed.
    echo         "unable to open database file" usually means the directory in
    echo         DATABASE_URL does not exist. Create it and re-run.
    popd
    goto fail
)
echo   [OK] Database ready

py %PYTAG% create_indexes.py
if errorlevel 1 (
    echo [WARN] create_indexes.py failed - indexes not created.
    echo        Check that DATABASE_URL is a plain sqlite:/// URL, not sqlite+aiosqlite.
)

py %PYTAG% write_version_file.py
popd
echo.

REM ---------------------------------------------------------------------------
REM  [9/10] Frontend
REM ---------------------------------------------------------------------------
echo [9/10] Frontend: npm install and build...
pushd "%PORTAL_DIR%\frontend"
call npm install
if errorlevel 1 (
    echo [ERROR] npm install failed.
    popd
    goto fail
)
call npm run build
if errorlevel 1 (
    echo [ERROR] npm run build failed - check the TypeScript errors above.
    popd
    goto fail
)
popd
echo [OK] Frontend built
echo.

REM ---------------------------------------------------------------------------
REM  [10/10] Windows service + firewall
REM ---------------------------------------------------------------------------
echo [10/10] Installing Windows service and firewall rule...

REM  Point the service at py.exe rather than a resolved uvicorn.exe path:
REM  py.exe lives in C:\Windows and is always visible to LocalSystem, whereas
REM  a Scripts\uvicorn.exe under a per-user Python install is not.
set "PYEXE="
for /f "usebackq tokens=*" %%p in (`where py`) do if not defined PYEXE set "PYEXE=%%p"
if not defined PYEXE (
    echo [ERROR] py.exe not found on PATH.
    goto fail
)
echo   launcher: %PYEXE%

if not exist "%PORTAL_DIR%\logs" mkdir "%PORTAL_DIR%\logs"

sc query %SVCNAME% >nul 2>&1
if not errorlevel 1 (
    echo   Removing previous %SVCNAME% service...
    nssm stop %SVCNAME% >nul 2>&1
    nssm remove %SVCNAME% confirm >nul 2>&1
    REM  A service still "marked for deletion" makes every nssm set below fail.
    timeout /t 3 /nobreak >nul
)

nssm install %SVCNAME% "%PYEXE%"
if errorlevel 1 (
    echo [ERROR] nssm install failed.
    echo         If the old service is "marked for deletion", close services.msc
    echo         and Task Manager, then re-run this script.
    goto fail
)

REM  WORKERS is deliberately 1. main.py starts APScheduler on startup with no
REM  worker guard, so N workers = N schedulers = every sync job firing N times.
nssm set %SVCNAME% AppDirectory "%PORTAL_DIR%\backend"
nssm set %SVCNAME% AppParameters "%PYTAG% -m uvicorn app.main:app --host 0.0.0.0 --port %PORT% --workers %WORKERS%"
nssm set %SVCNAME% DisplayName "Portal Backend"
nssm set %SVCNAME% Description "Portal FastAPI backend"
nssm set %SVCNAME% Start SERVICE_AUTO_START
nssm set %SVCNAME% AppStdout "%PORTAL_DIR%\logs\portal_stdout.log"
nssm set %SVCNAME% AppStderr "%PORTAL_DIR%\logs\portal_stderr.log"
nssm set %SVCNAME% AppRotateFiles 1
nssm set %SVCNAME% AppRotateBytes 10485760
REM  Same emoji/Chinese encoding trap as above, but for the running service.
nssm set %SVCNAME% AppEnvironmentExtra PYTHONIOENCODING=utf-8

nssm start %SVCNAME%
if errorlevel 1 (
    echo [ERROR] Service failed to start.
    echo         Log: %PORTAL_DIR%\logs\portal_stderr.log
    goto fail
)

netsh advfirewall firewall delete rule name="Portal Port %PORT%" >nul 2>&1
netsh advfirewall firewall add rule name="Portal Port %PORT%" dir=in action=allow protocol=TCP localport=%PORT% >nul
echo [OK] Service installed, firewall port %PORT% opened
echo.

REM ---------------------------------------------------------------------------
REM  Health check - "service started" is not the same as "app is serving"
REM ---------------------------------------------------------------------------
echo Waiting for the backend to answer...
timeout /t 8 /nobreak >nul
call :healthcheck
echo.

echo =========================================================
echo   Bootstrap complete
echo =========================================================
nssm status %SVCNAME%
echo.
git -C "%PORTAL_DIR%" log --oneline -1
echo.
echo   Open:  http://^<this-server-ip^>:%PORT%
echo   Logs:  %PORTAL_DIR%\logs\portal_stderr.log
echo.
echo   Next steps:
echo     1. Log in and change the default admin password.
echo     2. Verify Ragic connectivity with a manual sync:
echo          cd /d %PORTAL_DIR% ^&^& py %PYTAG% sync_tool.py
echo     3. Confirm the worker count is 1:
echo          nssm get %SVCNAME% AppParameters
echo     4. From now on use prod-update.bat to deploy updates.
echo.
pause
exit /b 0

REM ===========================================================================
REM  Subroutines
REM ===========================================================================

REM  :needkey KEY - append KEY to ENVBAD unless %ENVCHK% has a non-empty value.
REM  The character class is what makes this work on CRLF files: a bare "not a
REM  space" test would accept the trailing CR of an empty "KEY=" line.
REM  Do not put "!" in the class - delayed expansion would eat it.
:needkey
findstr /r /c:"^ *%~1 *=.*[0-9A-Za-z_/:.-]" "%ENVCHK%" >nul 2>&1
if errorlevel 1 set "ENVBAD=%ENVBAD% %~1"
exit /b 0

REM  :needenv - config.py accepts APP_ENV and ENV as aliases; either will do.
:needenv
findstr /r /c:"^ *APP_ENV *=.*[0-9A-Za-z_]" "%ENVCHK%" >nul 2>&1
if not errorlevel 1 exit /b 0
findstr /r /c:"^ *ENV *=.*[0-9A-Za-z_]" "%ENVCHK%" >nul 2>&1
if not errorlevel 1 exit /b 0
set "ENVBAD=%ENVBAD% APP_ENV(or ENV)"
exit /b 0

REM  :backup_env - timestamped backup of an existing .env.
REM  Kept out of the main flow on purpose: a for/f whose command contains
REM  parentheses is fragile inside an if(...) block.
:backup_env
if not exist "%PORTAL_DIR%\backend\.env" exit /b 0
set "STAMP="
for /f "usebackq tokens=*" %%t in (`powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"`) do set "STAMP=%%t"
if not defined STAMP set "STAMP=backup"
echo   Existing .env found - backing up to .env.bak-%STAMP%
copy /y "%PORTAL_DIR%\backend\.env" "%PORTAL_DIR%\backend\.env.bak-%STAMP%" >nul
exit /b 0

:install_nssm
echo   Installing NSSM...
winget install -e --id NSSM.NSSM --accept-source-agreements --accept-package-agreements --silent >nul 2>&1
where nssm >nul 2>&1
if not errorlevel 1 exit /b 0
echo   winget package unavailable, downloading from nssm.cc instead...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $z=Join-Path $env:TEMP 'nssm.zip'; $d=Join-Path $env:TEMP 'nssmx'; Invoke-WebRequest -Uri 'https://nssm.cc/release/nssm-2.24.zip' -OutFile $z; Expand-Archive -Path $z -DestinationPath $d -Force; Copy-Item (Join-Path $d 'nssm-2.24\win64\nssm.exe') 'C:\Windows\System32\nssm.exe' -Force"
exit /b 0

:healthcheck
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r=Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:%PORT%/api/v1/version' -TimeoutSec 10; Write-Host ('[OK] Backend responded: HTTP ' + $r.StatusCode) } catch { Write-Host '[WARN] Backend did not answer yet. It may still be starting; check the log.' }"
exit /b 0

:fail
echo.
echo [ABORTED] Fix the item above and re-run - completed steps are skipped.
echo           Note: depending on how far it got, tools may already be
echo           installed and %PORTAL_DIR% may already exist. Re-running is safe.
echo.
pause
exit /b 1
