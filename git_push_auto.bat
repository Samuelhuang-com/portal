@echo off
chcp 65001 >nul
title Git Push Auto

REM -- anti-close: open new window
if not "%GIT_LAUNCHED%"=="1" (
    set GIT_LAUNCHED=1
    start "Git Push Auto" cmd /k ""%~f0""
    exit /b
)

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
