@echo off
chcp 65001 >nul

REM ── 防止雙擊閃退 ──────────────────────────────────────────────────────────────
if not "%PROD_LAUNCHED%"=="1" (
    set PROD_LAUNCHED=1
    cmd /k ""%~f0""
    exit /b
)

cd /d D:\portal

echo.
echo ======================================
echo  Portal 正式區更新工具  v3
echo ======================================
echo.

REM ── 確認 Python 3.12 可用 ────────────────────────────────────────────────────
py -3.12 --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 找不到 Python 3.12！
    pause
    exit /b 1
)
echo [OK] Python 3.12 確認可用

REM ── 清除殘留 index.lock ──────────────────────────────────────────────────────
if exist .git\index.lock (
    echo [WARN] 發現殘留 .git\index.lock，自動清除...
    del /f .git\index.lock
    echo [OK] index.lock 已清除
)
echo.

REM ── Step 1: Git Pull ─────────────────────────────────────────────────────────
echo [1/5] 從 GitHub 拉最新版本...
echo.

REM 記錄 pull 前的 commit hash，方便比對差異
for /f %%i in ('git rev-parse HEAD 2^>nul') do set BEFORE_HASH=%%i

git stash

if exist run_sync_tool.bat (
    del /f run_sync_tool.bat
    echo [INFO] 已移除 untracked run_sync_tool.bat
)

git pull origin main
if errorlevel 1 (
    echo [ERROR] git pull 失敗，請檢查網路或 GitHub 授權。
    pause
    exit /b 1
)

git stash drop >nul 2>&1

REM ── 顯示本次拉下來的 commit 清單 ─────────────────────────────────────────────
echo.
echo ----------------------------------------
echo 本次更新內容（新增的 commits）：
echo ----------------------------------------
git log %BEFORE_HASH%..HEAD --oneline
for /f %%i in ('git log %BEFORE_HASH%..HEAD --oneline ^| find /c /v ""') do set NEW_COMMITS=%%i
if "%NEW_COMMITS%"=="0" (
    echo  （無新 commit，已是最新版）
)
echo.
echo 最新 commit：
git log --oneline -1
echo ----------------------------------------
echo.
echo  完成：程式碼已更新  ^| 下一步：安裝後端套件 [2/5]
echo.
pause

REM ── Step 2: 後端套件 ─────────────────────────────────────────────────────────
echo.
echo [2/5] 安裝後端套件 - Python 3.12...
cd /d D:\portal\backend
py -3.12 -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] pip install 失敗！
    pause
    exit /b 1
)
echo  完成：後端套件安裝完畢  ^| 下一步：建立 DB Index [3/5]
echo.
pause

REM ── Step 3: DB Index ─────────────────────────────────────────────────────────
echo.
echo [3/5] 建立 DB Index...
cd /d D:\portal\backend
py -3.12 create_indexes.py
if errorlevel 1 (
    echo [WARN] create_indexes.py 回傳錯誤，請確認是否影響功能。
)
echo  完成：DB Index 確認完畢  ^| 下一步：編譯前端 [4/5]
echo.
pause

REM ── Step 4: 前端 build ───────────────────────────────────────────────────────
echo.
echo [4/5] 安裝前端套件並編譯...
cd /d D:\portal\frontend

if not exist package.json (
    echo [SKIP] package.json not found，跳過前端 build。
    goto step5
)

npm install --silent
if errorlevel 1 (
    echo [ERROR] npm install 失敗！
    pause
    exit /b 1
)

npm run build
if errorlevel 1 (
    echo.
    echo [ERROR] npm run build 失敗！請檢查上方 TypeScript 編譯錯誤。
    pause
    exit /b 1
)

echo.
echo  前端編譯成功，dist 已更新：
dir D:\portal\frontend\dist\assets\*.js | findstr /v "^$"

:step5

REM ── Step 5: 重啟 uvicorn ─────────────────────────────────────────────────────
echo.
echo [5/5] 重啟正式服務...
echo.

REM 嘗試用 NSSM 重啟（服務名稱：portal）
sc query portal >nul 2>&1
if not errorlevel 1 (
    echo [NSSM] 偵測到 portal 服務，執行 restart...
    net stop portal
    net start portal
    echo [OK] portal 服務已重啟
    goto done
)

REM NSSM 服務不存在時，改用 taskkill + 重新啟動
echo [INFO] 未偵測到 NSSM 服務，改用 taskkill 方式重啟...
echo.

REM 關閉佔用 port 8000 的 uvicorn 程序
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    echo [INFO] 終止 PID %%p（port 8000）...
    taskkill /PID %%p /F >nul 2>&1
)

timeout /t 2 /nobreak >nul

echo [INFO] 啟動新的 uvicorn...
start "Portal Backend" cmd /k "cd /d D:\portal\backend && py -3.12 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"

echo [OK] uvicorn 已在新視窗中啟動

:done
echo.
echo ======================================
echo  更新完成！
echo.
echo  最新 commit：
git -C D:\portal log --oneline -3
echo.
echo  前端：http://0.0.0.0:8000
echo ======================================
echo.
pause
