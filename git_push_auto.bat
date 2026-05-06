@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ==========================================
REM 自動 Git Commit + Push
REM 路徑：C:\OneDrive\_Ragic\portal
REM Commit 格式：fix: YYYYMMDD-流水號
REM 範例：fix: 20260506-001
REM ==========================================

cd /d C:\OneDrive\_Ragic\portal

echo.
echo ==========================================
echo 目前目錄：
cd
echo ==========================================
echo.

REM 取得今天日期 YYYYMMDD
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd"') do set TODAY=%%i

REM 找出今天 commit message 中最大的流水號
for /f %%i in ('powershell -NoProfile -Command "$today='%TODAY%'; $msgs = git log --pretty=format:'%%s' --since='midnight' 2>$null; $nums = $msgs | ForEach-Object { if ($_ -match '^fix: '+$today+'-(\d+)$') { [int]$matches[1] } }; if ($nums) { ($nums | Measure-Object -Maximum).Maximum + 1 } else { 1 }"') do set SEQ=%%i

REM 補成三位數
set SEQ=00%SEQ%
set SEQ=%SEQ:~-3%

set COMMIT_MSG=fix: %TODAY%-%SEQ%

echo 本次 Commit Message：
echo %COMMIT_MSG%
echo.

REM 顯示目前變動
echo ==========================================
echo Git Status
echo ==========================================
git status --short
echo.

REM 檢查是否有變動
git diff --quiet
set HAS_DIFF=%errorlevel%

git diff --cached --quiet
set HAS_CACHED_DIFF=%errorlevel%

if "%HAS_DIFF%"=="0" if "%HAS_CACHED_DIFF%"=="0" (
    echo 沒有偵測到任何檔案變動，不需要 commit。
    echo.
    pause
    exit /b 0
)

REM 加入所有變動
echo ==========================================
echo git add .
echo ==========================================
git add .

REM 建立 Commit
echo.
echo ==========================================
echo git commit
echo ==========================================
git commit -m "%COMMIT_MSG%"

if errorlevel 1 (
    echo.
    echo Commit 失敗，請檢查錯誤訊息。
    pause
    exit /b 1
)

REM 推上 GitHub
echo.
echo ==========================================
echo git push
echo ==========================================
git push

if errorlevel 1 (
    echo.
    echo Push 失敗，請檢查 GitHub 權限、網路或分支設定。
    pause
    exit /b 1
)

echo.
echo ==========================================
echo 完成！
echo %COMMIT_MSG%
echo ==========================================
pause