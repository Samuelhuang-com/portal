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
REM      bootstrap.bat "E:\backup\.env" "C:\portal"    (install elsewhere)
REM      bootstrap.bat                 (will prompt for the .env path)
REM
REM  Arg 1 may be the .env file itself OR a folder containing .env or
REM  backend\.env - the script resolves it either way.
REM  Arg 2 overrides the install directory (default below).
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
if not "%~2"=="" set "PORTAL_DIR=%~2"

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
call :resolve_env
if errorlevel 1 goto fail
if not exist "!ENVSRC!" (
    echo [ERROR] .env not found: !ENVSRC!
    echo.
    echo   Give the full path to the .env FILE, for example:
    echo       E:\backup\.env
    echo   A folder also works if it contains .env or backend\.env.
    goto fail
)

set "ENVCHK=!ENVSRC!"
call :validate_env
if errorlevel 1 (
    echo.
    echo         File checked: !ENVSRC!
    echo.
    echo   CYCLE_PURCHASE_DATABASE_URL and DATABASE_URL are the ones that get
    echo   left out. When they are absent the backend does NOT fail - it
    echo   silently falls back to a relative path, the migration scripts then
    echo   write to a DIFFERENT file, and every symptom points somewhere else.
    echo   See CHANGELOG [1.90.29].
    echo.
    echo   Fix the SOURCE file above, then re-run. Nothing has been changed yet.
    goto fail
)
echo [OK] Source .env validated: !ENVSRC!
echo.

REM ---------------------------------------------------------------------------
REM  [3/10] winget availability
REM ---------------------------------------------------------------------------
echo [3/10] Choosing an install method...
set "USEWINGET=1"
where winget >nul 2>&1
if errorlevel 1 set "USEWINGET="
if defined USEWINGET (
    echo [OK] winget available
) else (
    echo [INFO] winget not found - falling back to direct download from the
    echo        official sites. Windows Server does not ship App Installer,
    echo        and winget's Store endpoints are often blocked anyway.
    echo        This machine still needs outbound HTTPS to:
    echo          api.github.com / github.com   ^(Git^)
    echo          www.python.org                ^(Python^)
    echo          nodejs.org                    ^(Node.js^)
    echo          nssm.cc                       ^(NSSM^)
)
echo.

REM ---------------------------------------------------------------------------
REM  [4/10] Install toolchain
REM
REM  --scope machine matters: NSSM runs the service as LocalSystem, which
REM  cannot see a per-user Python under C:\Users\...\AppData.
REM ---------------------------------------------------------------------------
echo [4/10] Installing toolchain (already-present items are skipped)...

where git >nul 2>&1
if errorlevel 1 (call :inst_git) else (echo   [skip] Git already installed)

py %PYTAG% --version >nul 2>&1
if errorlevel 1 (call :inst_python) else (echo   [skip] Python 3.12 already installed)

where node >nul 2>&1
if errorlevel 1 (call :inst_node) else (echo   [skip] Node.js already installed)

where nssm >nul 2>&1
if errorlevel 1 (call :install_nssm) else (echo   [skip] NSSM already installed)
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

REM  :validate_env - check %ENVCHK% for the keys the backend cannot run without.
REM
REM  This was originally a set of findstr /r tests. Do not go back to that.
REM  On a real .env, findstr reported DATABASE_URL, CYCLE_PURCHASE_DATABASE_URL
REM  and RAGIC_API_KEY as present when the file contained none of them - a
REM  false PASS on exactly the keys this check exists to catch.
REM  PowerShell parses the file properly: BOM, CRLF, tabs, spaces around "=",
REM  quoted values and comments all behave.
REM
REM  Aliases handled (see backend/app/core/config.py):
REM    SECRET_KEY  or  JWT_SECRET_KEY   (JWT_SECRET_KEY wins when both are set)
REM    APP_ENV     or  ENV
REM  -Encoding UTF8 is NOT optional. PowerShell 5.1 defaults Get-Content to the
REM  system ANSI codepage (cp950 on a Traditional Chinese Windows). A UTF-8
REM  .env with Chinese comments then decodes as double-byte pairs, the byte
REM  alignment slips, and a CR/LF gets swallowed as somebody's trail byte -
REM  so the next line's key is no longer at the start of a line and every
REM  ^KEY= match silently fails. Observed on a real .env: three keys that were
REM  present were all reported missing.
:validate_env
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p='%ENVCHK%'; $h=@{}; foreach($l in (Get-Content -LiteralPath $p -Encoding UTF8)){ if($l -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$'){ $h[$matches[1]] = $matches[2].Trim().Trim('\"').Trim([char]39) } }; function Has($k){ return $h.ContainsKey($k) -and $h[$k] -ne '' }; $bad=@(); foreach($k in @('RAGIC_API_KEY','DATABASE_URL','CYCLE_PURCHASE_DATABASE_URL','CORS_ORIGINS')){ if(-not (Has $k)){ $bad += $k } }; if(-not ((Has 'SECRET_KEY') -or (Has 'JWT_SECRET_KEY'))){ $bad += 'SECRET_KEY or JWT_SECRET_KEY' }; if(-not ((Has 'APP_ENV') -or (Has 'ENV'))){ $bad += 'APP_ENV or ENV' }; if((Has 'SECRET_KEY') -and $h['SECRET_KEY'] -like '*change-me*'){ $bad += 'SECRET_KEY is still the placeholder' }; if($bad.Count -gt 0){ Write-Host ''; Write-Host '[ERROR] Source .env is missing or has empty values for:'; foreach($b in $bad){ Write-Host ('          - ' + $b) }; exit 1 }; Write-Host ('        DATABASE_URL                = ' + $h['DATABASE_URL']); Write-Host ('        CYCLE_PURCHASE_DATABASE_URL = ' + $h['CYCLE_PURCHASE_DATABASE_URL']); exit 0"
exit /b %errorlevel%

REM  :resolve_env - accept a folder as well as a file. People reach for the
REM  folder they keep the backup in, not the hidden dotfile inside it.
:resolve_env
if not exist "%ENVSRC%\" exit /b 0
if exist "%ENVSRC%\.env" set "ENVSRC=%ENVSRC%\.env" & exit /b 0
if exist "%ENVSRC%\backend\.env" set "ENVSRC=%ENVSRC%\backend\.env" & exit /b 0
echo [ERROR] That is a folder, and it contains no .env
echo         Looked for: %ENVSRC%\.env
echo                and: %ENVSRC%\backend\.env
exit /b 1

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

REM ---------------------------------------------------------------------------
REM  Toolchain installers.
REM
REM  Each tries winget first (when available) and otherwise downloads the
REM  official installer. Versions are resolved AT RUNTIME rather than pinned,
REM  so these do not rot: hard-coded installer URLs go stale within months.
REM  All three are silent/unattended and machine-scoped - a per-user Python
REM  is invisible to the LocalSystem account the service runs under.
REM ---------------------------------------------------------------------------

:inst_git
echo   Installing Git...
if defined USEWINGET winget install -e --id Git.Git --scope machine --accept-source-agreements --accept-package-agreements --silent
where git >nul 2>&1
if not errorlevel 1 exit /b 0
echo   Downloading Git for Windows from github.com...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; $r=Invoke-RestMethod -Uri 'https://api.github.com/repos/git-for-windows/git/releases/latest' -Headers @{'User-Agent'='portal-bootstrap'}; $a=$r.assets | Where-Object { $_.name -like '*-64-bit.exe' } | Select-Object -First 1; if(-not $a){ throw 'no 64-bit installer in the latest release' }; $f=Join-Path $env:TEMP $a.name; Write-Host ('    ' + $a.name); Invoke-WebRequest -Uri $a.browser_download_url -OutFile $f -UseBasicParsing; Write-Host '    installing (silent)...'; Start-Process -FilePath $f -ArgumentList '/VERYSILENT','/NORESTART','/SP-' -Wait"
exit /b 0

:inst_python
echo   Installing Python 3.12...
if defined USEWINGET winget install -e --id Python.Python.3.12 --scope machine --accept-source-agreements --accept-package-agreements --silent
py %PYTAG% --version >nul 2>&1
if not errorlevel 1 exit /b 0
echo   Downloading Python 3.12 from python.org...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; $h=(Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/' -UseBasicParsing).Content; $ns=[regex]::Matches($h,'3\.12\.([0-9]+)/') | ForEach-Object { [int]$_.Groups[1].Value } | Sort-Object -Unique -Descending; if($ns.Count -eq 0){ throw 'no 3.12.x directory listed' }; $u=$null; foreach($n in $ns){ $c='https://www.python.org/ftp/python/3.12.'+$n+'/python-3.12.'+$n+'-amd64.exe'; try { Invoke-WebRequest -Uri $c -Method Head -UseBasicParsing | Out-Null; $u=$c; break } catch { } }; if(-not $u){ $u='https://www.python.org/ftp/python/3.12.'+$ns[0]+'/python-3.12.'+$ns[0]+'-amd64.exe' }; $f=Join-Path $env:TEMP 'python-3.12-amd64.exe'; Write-Host ('    ' + $u); Invoke-WebRequest -Uri $u -OutFile $f -UseBasicParsing; Write-Host '    installing (silent, all users, PATH)...'; Start-Process -FilePath $f -ArgumentList '/quiet','InstallAllUsers=1','PrependPath=1','Include_launcher=1','Include_pip=1' -Wait"
exit /b 0

:inst_node
echo   Installing Node.js LTS...
if defined USEWINGET winget install -e --id OpenJS.NodeJS.LTS --scope machine --accept-source-agreements --accept-package-agreements --silent
where node >nul 2>&1
if not errorlevel 1 exit /b 0
echo   Downloading Node.js LTS from nodejs.org...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; $j=Invoke-RestMethod -Uri 'https://nodejs.org/dist/index.json'; $l=$j | Where-Object { $_.lts } | Select-Object -First 1; if(-not $l){ throw 'no LTS release listed' }; $u='https://nodejs.org/dist/'+$l.version+'/node-'+$l.version+'-x64.msi'; $f=Join-Path $env:TEMP 'node-lts-x64.msi'; Write-Host ('    ' + $u); Invoke-WebRequest -Uri $u -OutFile $f -UseBasicParsing; Write-Host '    installing (silent)...'; Start-Process msiexec.exe -ArgumentList '/i',$f,'/qn','/norestart' -Wait"
exit /b 0

:install_nssm
echo   Installing NSSM...
if defined USEWINGET winget install -e --id NSSM.NSSM --accept-source-agreements --accept-package-agreements --silent >nul 2>&1
where nssm >nul 2>&1
if not errorlevel 1 exit /b 0
echo   Downloading NSSM from nssm.cc...
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
