@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

cd /d C:\OneDrive\_Ragic\portal

echo.
echo ==========================================
powershell -NoProfile -Command "Write-Host '目前目錄：'"
cd
echo ==========================================
echo.

REM -- clear stale index.lock
if exist .git\index.lock (
    powershell -NoProfile -Command "Write-Host '[WARN] 發現殘留 .git\index.lock，自動清除...' -ForegroundColor Yellow"
    del /f .git\index.lock
    powershell -NoProfile -Command "Write-Host '[OK] index.lock 已清除' -ForegroundColor Green"
    echo.
)

REM -- get date YYYYMMDD
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd"') do set TODAY=%%i

REM -- find max sequence number today
for /f %%i in ('powershell -NoProfile -Command "$today='%TODAY%'; $msgs = git log --pretty=format:\"%%s\" --since='midnight' 2>$null; $nums = $msgs | ForEach-Object { if ($_ -match ('^fix: '+$today+'-(\d+)$')) { [int]$Matches[1] } }; if ($nums) { ($nums | Measure-Object -Maximum).Maximum + 1 } else { 1 }"') do set SEQ=%%i

set SEQ=00%SEQ%
set SEQ=%SEQ:~-3%
set COMMIT_MSG=fix: %TODAY%-%SEQ%

powershell -NoProfile -Command "Write-Host 'Commit Message: %COMMIT_MSG%' -ForegroundColor Cyan"
echo.

REM -- show changed files
echo ==========================================
powershell -NoProfile -Command "Write-Host '異動檔案清單：'"
echo ==========================================
git status --short
echo.

REM -- check if anything changed
for /f %%i in ('git status --porcelain ^| find /c /v ""') do set CHANGED=%%i
if "%CHANGED%"=="0" (
    powershell -NoProfile -Command "Write-Host '沒有偵測到任何檔案變動，不需要 commit。' -ForegroundColor Yellow"
    echo.
    pause
    exit /b 0
)

REM -- git add
echo ==========================================
echo git add .
echo ==========================================
git add .
if errorlevel 1 (
    powershell -NoProfile -Command "Write-Host '[ERROR] git add 失敗！' -ForegroundColor Red"
    pause
    exit /b 1
)

REM -- show what will be committed
echo.
echo ==========================================
powershell -NoProfile -Command "Write-Host '即將 commit 的檔案：'"
echo ==========================================
git diff --cached --stat
echo.

REM -- git commit
echo ==========================================
echo git commit
echo ==========================================
git commit -m "%COMMIT_MSG%"
if errorlevel 1 (
    powershell -NoProfile -Command "Write-Host 'Commit 失敗，請檢查錯誤訊息。' -ForegroundColor Red"
    pause
    exit /b 1
)

REM -- git push
echo.
echo ==========================================
echo git push
echo ==========================================
git push origin main
if errorlevel 1 (
    powershell -NoProfile -Command "Write-Host 'Push 失敗，請檢查 GitHub 權限或網路。' -ForegroundColor Red"
    pause
    exit /b 1
)

REM -- done: show latest commits
echo.
echo ==========================================
powershell -NoProfile -Command "Write-Host '完成！已推上 GitHub' -ForegroundColor Green"
echo ==========================================
echo.
powershell -NoProfile -Command "Write-Host '最新 5 筆 commit：'"
git log --oneline -5
echo.
echo ==========================================
pause
