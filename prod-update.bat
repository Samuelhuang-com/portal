@echo off
chcp 65001 >nul
cd /d D:\portal

echo.
echo ======================================
echo  Portal 正式區更新工具  v2
echo ======================================
echo.

REM ── 確認 Python 3.12 可用 ────────────────────────────────────────────────────
py -3.12 --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 找不到 Python 3.12！
    echo         請先至 https://www.python.org 安裝 Python 3.12，
    echo         或確認 py launcher 能找到 3.12（py -3.12 --version）
    echo.
    pause
    exit /b 1
)
echo [OK] Python 3.12 確認可用
echo.

REM ── Step 1: Git Pull ─────────────────────────────────────────────────────────
echo [1/5] 從 GitHub 拉最新版本...
git stash
git pull origin main
if errorlevel 1 (
    echo [ERROR] git pull failed, please check error message above.
    pause
    exit /b 1
)
echo.
echo  完成: 程式碼已更新
echo  下一步: 安裝後端套件 [2/5]
echo.
pause

REM ── Step 2: 後端套件 ─────────────────────────────────────────────────────────
echo.
echo [2/5] 安裝後端套件 - Python 3.12...
cd /d D:\portal\backend
py -3.12 -m pip install -r requirements.txt
echo.
echo  完成: 後端套件安裝完畢
echo  下一步: 建立 DB Index [3/5]
echo.
pause

REM ── Step 3: DB Index ─────────────────────────────────────────────────────────
echo.
echo [3/5] 建立 DB Index...
cd /d D:\portal\backend
py -3.12 create_indexes.py
echo.
echo  完成: DB Index 確認完畢
echo  下一步: 編譯前端 [4/5]
echo.
pause

REM ── Step 4: 前端 build ───────────────────────────────────────────────────────
echo.
echo [4/5] 安裝前端套件並編譯...
cd /d D:\portal\frontend

if not exist package.json (
    echo [SKIP] package.json not found, skipping frontend build.
    goto step5
)

npm install
if errorlevel 1 echo [WARN] npm install returned non-zero, continuing...

npm run build
if errorlevel 1 echo [WARN] npm run build returned non-zero - check output above

:step5
echo.
echo  完成: 前端編譯完畢
echo  下一步: 重新啟動正式服務 [5/5]
echo.
pause

REM ── Step 5: 完成提示 ─────────────────────────────────────────────────────────
echo.
echo [5/5] 所有步驟完成！
echo.
echo  請重新啟動 uvicorn 正式服務
echo.
echo  指令啟動範例:
echo    cd D:\portal\backend
echo    py -3.12 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
echo.
echo  若使用 NSSM 或工作排程器，請在服務管理員重啟 Portal 服務。
echo.
pause