@echo off
chcp 65001 >nul

REM -- prevent auto-close on double-click
if not "%PROD_LAUNCHED%"=="1" (
    set PROD_LAUNCHED=1
    cmd /k ""%~f0""
    exit /b
)

cd /d D:\portal

echo.
echo ======================================
powershell -NoProfile -Command "Write-Host ' Portal 正式區更新工具  v3' -ForegroundColor Cyan"
echo ======================================
echo.

REM -- check Python 3.12
py -3.12 --version >nul 2>&1
if errorlevel 1 (
    powershell -NoProfile -Command "Write-Host '[ERROR] 找不到 Python 3.12！' -ForegroundColor Red"
    pause
    exit /b 1
)
powershell -NoProfile -Command "Write-Host '[OK] Python 3.12 確認可用' -ForegroundColor Green"

REM -- clear stale index.lock
if exist .git\index.lock (
    powershell -NoProfile -Command "Write-Host '[WARN] 發現殘留 .git\index.lock，自動清除...' -ForegroundColor Yellow"
    del /f .git\index.lock
    powershell -NoProfile -Command "Write-Host '[OK] index.lock 已清除' -ForegroundColor Green"
)
echo.

REM ── Step 1: Git Pull ─────────────────────────────────────────────────────────
powershell -NoProfile -Command "Write-Host '[1/5] 從 GitHub 拉最新版本...' -ForegroundColor Cyan"
echo.

for /f %%i in ('git rev-parse HEAD 2^>nul') do set BEFORE_HASH=%%i

git stash

if exist run_sync_tool.bat (
    del /f run_sync_tool.bat
    powershell -NoProfile -Command "Write-Host '[INFO] 已移除 untracked run_sync_tool.bat'"
)

git pull origin main
if errorlevel 1 (
    powershell -NoProfile -Command "Write-Host '[ERROR] git pull 失敗！' -ForegroundColor Red"
    pause
    exit /b 1
)

git stash drop >nul 2>&1

REM -- show new commits pulled
echo.
echo ----------------------------------------
powershell -NoProfile -Command "Write-Host '本次更新內容（新增的 commits）：' -ForegroundColor Yellow"
echo ----------------------------------------
git log %BEFORE_HASH%..HEAD --oneline
for /f %%i in ('git log %BEFORE_HASH%..HEAD --oneline ^| find /c /v ""') do set NEW_COMMITS=%%i
if "%NEW_COMMITS%"=="0" (
    powershell -NoProfile -Command "Write-Host '  （無新 commit，已是最新版）'"
)
echo.
powershell -NoProfile -Command "Write-Host '最新 commit：' -ForegroundColor White"
git log --oneline -1
echo ----------------------------------------
echo.
powershell -NoProfile -Command "Write-Host '完成：程式碼已更新  |  下一步：安裝後端套件 [2/5]' -ForegroundColor Green"
echo.
pause

REM ── Step 2: 後端套件 ─────────────────────────────────────────────────────────
echo.
powershell -NoProfile -Command "Write-Host '[2/5] 安裝後端套件 - Python 3.12...' -ForegroundColor Cyan"
cd /d D:\portal\backend
py -3.12 -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    powershell -NoProfile -Command "Write-Host '[ERROR] pip install 失敗！' -ForegroundColor Red"
    pause
    exit /b 1
)
powershell -NoProfile -Command "Write-Host '完成：後端套件安裝完畢  |  下一步：建立 DB Index [3/5]' -ForegroundColor Green"
echo.
pause

REM ── Step 3: DB Index ─────────────────────────────────────────────────────────
echo.
powershell -NoProfile -Command "Write-Host '[3/5] 建立 DB Index...' -ForegroundColor Cyan"
cd /d D:\portal\backend
py -3.12 create_indexes.py
powershell -NoProfile -Command "Write-Host '完成：DB Index 確認完畢  |  下一步：編譯前端 [4/5]' -ForegroundColor Green"
echo.
pause

REM ── Step 4: 前端 build ───────────────────────────────────────────────────────
echo.
powershell -NoProfile -Command "Write-Host '[4/5] 安裝前端套件並編譯...' -ForegroundColor Cyan"
cd /d D:\portal\frontend

if not exist package.json (
    powershell -NoProfile -Command "Write-Host '[SKIP] package.json 不存在，跳過前端 build。' -ForegroundColor Yellow"
    goto step5
)

npm install --silent
if errorlevel 1 (
    powershell -NoProfile -Command "Write-Host '[ERROR] npm install 失敗！' -ForegroundColor Red"
    pause
    exit /b 1
)

npm run build
if errorlevel 1 (
    echo.
    powershell -NoProfile -Command "Write-Host '[ERROR] npm run build 失敗！請檢查上方 TypeScript 錯誤。' -ForegroundColor Red"
    pause
    exit /b 1
)

echo.
powershell -NoProfile -Command "Write-Host '前端編譯成功，dist 已更新：' -ForegroundColor Green"
dir D:\portal\frontend\dist\assets\*.js 2>nul | findstr /v "^$"

:step5

REM ── Step 5: 重啟 uvicorn ─────────────────────────────────────────────────────
echo.
powershell -NoProfile -Command "Write-Host '[5/5] 重啟正式服務...' -ForegroundColor Cyan"
echo.

REM -- try NSSM service named "portal"
sc query portal >nul 2>&1
if not errorlevel 1 (
    powershell -NoProfile -Command "Write-Host '[NSSM] 偵測到 portal 服務，執行 restart...' -ForegroundColor Yellow"
    net stop portal
    net start portal
    powershell -NoProfile -Command "Write-Host '[OK] portal 服務已重啟' -ForegroundColor Green"
    goto done
)

REM -- fallback: taskkill port 8000 + restart
powershell -NoProfile -Command "Write-Host '[INFO] 未偵測到 NSSM 服務，改用 taskkill 方式重啟...' -ForegroundColor Yellow"
echo.

for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    powershell -NoProfile -Command "Write-Host '[INFO] 終止 PID %%p（port 8000）...'"
    taskkill /PID %%p /F >nul 2>&1
)

timeout /t 2 /nobreak >nul

powershell -NoProfile -Command "Write-Host '[INFO] 啟動新的 uvicorn...' -ForegroundColor Yellow"
start "Portal Backend" cmd /k "cd /d D:\portal\backend && py -3.12 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"
powershell -NoProfile -Command "Write-Host '[OK] uvicorn 已在新視窗中啟動' -ForegroundColor Green"

:done
echo.
echo ======================================
powershell -NoProfile -Command "Write-Host '更新完成！' -ForegroundColor Green"
echo.
powershell -NoProfile -Command "Write-Host '最新 3 筆 commit：' -ForegroundColor White"
git -C D:\portal log --oneline -3
echo.
powershell -NoProfile -Command "Write-Host '前端入口：http://[伺服器IP]:8000' -ForegroundColor Cyan"
echo ======================================
echo.
pause
