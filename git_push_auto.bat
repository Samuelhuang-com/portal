@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ==========================================
REM 自動 Git Commit + Push  v3
REM 路徑：C:\OneDrive\_Ragic\portal
REM Commit 格式：fix: YYYYMMDD-流水號
REM ==========================================

cd /d C:\OneDrive\_Ragic\portal

echo.
echo ==========================================
echo 目前目錄：
cd
echo ==========================================
echo.

REM ── 清除殘留 index.lock ──────────────────────────────────────────────────────
if exist .git\index.lock (
    echo [WARN] 發現殘留 .git\index.lock，自動清除中...
    del /f .git\index.lock
    echo [OK] index.lock 已清除
    echo.
)

REM ── 取得今天日期 YYYYMMDD ──────────────────────────────────────────────────
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd"') do set TODAY=%%i

REM ── 找出今天最大流水號 ────────────────────────────────────────────────────
for /f %%i in ('powershell -NoProfile -Command "$today='%TODAY%'; $msgs = git log --pretty=format:\"%%s\" --since='midnight' 2>$null; $nums = $msgs | ForEach-Object { if ($_ -match ('^fix: '+$today+'-(\d+)$')) { [int]$Matches[1] } }; if ($nums) { ($nums | Measure-Object -Maximum).Maximum + 1 } else { 1 }"') do set SEQ=%%i

REM ── 補成三位數 ─────────────────────────────────────────────────────────────
set SEQ=00%SEQ%
set SEQ=%SEQ:~-3%
set COMMIT_MSG=fix: %TODAY%-%SEQ%

echo 本次 Commit Message：
echo %COMMIT_MSG%
echo.

REM ── 顯示異動檔案清單 ────────────────────────────────────────────────────────
echo ==========================================
echo 異動檔案清單（git status）
echo ==========================================
git status --short
echo.

REM ── 檢查是否有任何變動（含未追蹤新檔）──────────────────────────────────────
for /f %%i in ('git status --porcelain ^| find /c /v ""') do set CHANGED=%%i
if "%CHANGED%"=="0" (
    echo 沒有偵測到任何檔案變動，不需要 commit。
    echo.
    pause
    exit /b 0
)

REM ── git add ──────────────────────────────────────────────────────────────────
echo ==========================================
echo git add .
echo ==========================================
git add .
if errorlevel 1 (
    echo [ERROR] git add 失敗！
    pause
    exit /b 1
)

REM ── 顯示即將 commit 的內容 ────────────────────────────────────────────────
echo.
echo ==========================================
echo 即將 commit 的檔案：
echo ==========================================
git diff --cached --stat
echo.

REM ── git commit ───────────────────────────────────────────────────────────────
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

REM ── git push ─────────────────────────────────────────────────────────────────
echo.
echo ==========================================
echo git push
echo ==========================================
git push origin main
if errorlevel 1 (
    echo.
    echo Push 失敗，請檢查 GitHub 權限、網路或分支設定。
    pause
    exit /b 1
)

REM ── 完成：顯示最新 commit 摘要 ──────────────────────────────────────────────
echo.
echo ==========================================
echo 完成！已推上 GitHub
echo ==========================================
echo.
echo 最新 5 筆 commit：
git log --oneline -5
echo.
echo ==========================================
pause
