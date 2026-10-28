@echo off
chcp 65001 >nul
title Git Push Auto

REM -- anti-close: open new window
REM    NOTE: args are passed to the child via environment variables, not on the
REM          command line -- quoting through start/cmd /k is fragile.
REM if not "%GIT_LAUNCHED%"=="1" (
REM    set GIT_LAUNCHED=1
REM    if /i "%~1"=="--skip-tests" set SKIP_E2E=1
REM    if /i "%~1"=="-s"           set SKIP_E2E=1
REM    start "Git Push Auto" cmd /k ""%~f0""
REM    exit /b
REM )

setlocal enabledelayedexpansion

cd /d C:\OneDrive\_Ragic\portal

echo.
echo ==========================================
echo  Directory:
cd
echo ==========================================
echo.

REM -- clear stale index.lock
if exist .git\index.lock (
    echo [WARN] Removing stale .git\index.lock...
    del /f .git\index.lock
    echo [OK] index.lock removed
    echo.
)

REM -- get today YYYYMMDD
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd"') do set TODAY=%%i

REM -- find max sequence number today
for /f %%i in ('powershell -NoProfile -Command "$today='%TODAY%'; $msgs = git log --pretty=format:\"%%s\" --since='midnight' 2>$null; $nums = $msgs | ForEach-Object { if ($_ -match ('^fix: '+$today+'-(\d+)$')) { [int]$Matches[1] } }; if ($nums) { ($nums | Measure-Object -Maximum).Maximum + 1 } else { 1 }"') do set SEQ=%%i

set SEQ=00%SEQ%
set SEQ=%SEQ:~-3%
set COMMIT_MSG=fix: %TODAY%-%SEQ%

echo Commit Message: %COMMIT_MSG%
echo.

REM -- force re-read all file contents (fixes OneDrive mtime issue)
git update-index --really-refresh >nul 2>&1

REM -- show changed files
echo ==========================================
echo Changed files:
echo ==========================================
git status --short
echo.

REM -- check if anything changed
for /f %%i in ('git status --porcelain ^| find /c /v ""') do set CHANGED=%%i
if "%CHANGED%"=="0" (
    echo No changes detected. Nothing to commit.
    echo.
    echo Checking for unpushed commits...
    git push origin main
    if errorlevel 1 (
        echo [ERROR] Push failed! Check GitHub credentials or network.
        pause
        exit /b 1
    )
    echo.
    echo Latest 5 commits:
    git log --oneline -5
    echo.
    pause
    exit /b 0
)

REM -- git add (double-add for OneDrive reliability)
git add -A
git update-index --really-refresh >nul 2>&1
git add -A

if errorlevel 1 (
    echo [ERROR] git add failed!
    pause
    exit /b 1
)

REM -- show what will be committed
echo.
echo ==========================================
echo Files to be committed:
echo ==========================================
git diff --cached --name-status
echo.
git diff --cached --stat
echo.

REM -- check staged is not empty
for /f %%i in ('git diff --cached --name-only ^| find /c /v ""') do set STAGED=%%i
if "%STAGED%"=="0" (
    echo [WARN] Nothing staged. Aborting.
    pause
    exit /b 0
)

REM ==========================================================================
REM  E2E gate -- DISABLED 2026-08-25 (by request).
REM
REM  This script no longer runs Playwright. Run the tests separately with:
REM      run_e2e.bat                 (full suite)
REM      run_e2e.bat luqun-repair    (one spec file, or a --grep keyword)
REM      run_e2e.bat --ui            (Playwright UI / debug mode)
REM      run_e2e.bat --report        (open the last HTML report)
REM
REM  The whole original gate is kept below, commented out. To bring it back,
REM  strip the leading "REM|" from every line between the two ---8<--- markers.
REM ==========================================================================

REM ---8<--- original E2E gate begins ---8<---
REM|REM ==========================================================================
REM|REM  E2E gate -- runs BEFORE commit, so bad code never enters the shared repo.
REM|REM
REM|REM  Rules:
REM|REM    * only runs when staged files include frontend/  (docs / backend / bat
REM|REM      changes are not slowed down)
REM|REM    * requires the backend on :8000  (the frontend dev server is started
REM|REM      automatically by playwright.config.ts -> webServer)
REM|REM    * failure aborts the commit; use "git_push_auto.bat --skip-tests" to
REM|REM      override, which prints an explicit UNVERIFIED warning
REM|REM ==========================================================================
REM|if "%SKIP_E2E%"=="1" goto :e2e_skipped
REM|
REM|REM -- count staged files under frontend/  (PowerShell, not findstr: findstr
REM|REM    chokes on UTF-8 filenames)
REM|set FE_CHANGED=
REM|for /f %%i in ('powershell -NoProfile -Command "(git diff --cached --name-only ^| Where-Object { $_ -like 'frontend/*' } ^| Measure-Object).Count"') do set FE_CHANGED=%%i
REM|REM -- if the count could not be determined, err on the side of running the tests
REM|if not defined FE_CHANGED set FE_CHANGED=1
REM|
REM|if "%FE_CHANGED%"=="0" (
REM|    echo [SKIP] No frontend/ changes staged -- E2E not needed.
REM|    echo.
REM|    goto :e2e_done
REM|)
REM|
REM|echo ==========================================
REM|echo  E2E gate: %FE_CHANGED% frontend file^(s^) staged
REM|echo ==========================================
REM|echo.
REM|echo Checking backend on 127.0.0.1:8000 ...
REM|powershell -NoProfile -Command "try { $null = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/v1/version' -TimeoutSec 5 -UseBasicParsing; exit 0 } catch { exit 1 }"
REM|if errorlevel 1 (
REM|    echo.
REM|    echo [ERROR] Backend is not responding on 127.0.0.1:8000
REM|    echo         Start it first:  cd backend ^&^& uvicorn app.main:app --reload --port 8000
REM|    echo         Or skip:         git_push_auto.bat --skip-tests
REM|    echo.
REM|    echo Nothing was committed.
REM|    pause
REM|    exit /b 1
REM|)
REM|echo [OK] Backend is up.
REM|echo.
REM|echo Running Playwright E2E ^(this takes a couple of minutes^)...
REM|echo.
REM|pushd frontend
REM|call npm run test:e2e
REM|set E2E_EXIT=!errorlevel!
REM|popd
REM|
REM|if not "!E2E_EXIT!"=="0" (
REM|    echo.
REM|    echo ==========================================
REM|    echo  [ERROR] E2E FAILED -- commit aborted
REM|    echo ==========================================
REM|    echo  Files are still staged. Fix and re-run this script.
REM|    echo  Report:  cd frontend ^&^& npx playwright show-report
REM|    echo.
REM|    pause
REM|    exit /b 1
REM|)
REM|echo.
REM|echo [OK] E2E passed.
REM|echo.
REM|goto :e2e_done
REM|
REM|:e2e_skipped
REM|echo ==========================================
REM|echo  [WARN] --skip-tests: E2E was NOT run.
REM|echo         THIS PUSH IS UNVERIFIED.
REM|echo ==========================================
REM|echo.
REM|
REM|:e2e_done
REM ---8<--- original E2E gate ends ---8<---


REM -- git commit
git commit -m "%COMMIT_MSG%"
if errorlevel 1 (
    echo [ERROR] Commit failed!
    pause
    exit /b 1
)

REM -- git push
echo.
git push origin main
if errorlevel 1 (
    echo [ERROR] Push failed! Check GitHub credentials or network.
    pause
    exit /b 1
)

REM -- done
echo.
echo ==========================================
echo Done! Pushed to GitHub: %COMMIT_MSG%
echo ==========================================
echo.
echo Latest 5 commits:
git log --oneline -5
echo.
echo ==========================================
pause
