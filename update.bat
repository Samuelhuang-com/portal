@echo off
chcp 65001 >nul

echo.
echo [Portal] 從 GitHub 更新程式碼...
echo.

cd /d D:\portal

echo [1/3] 同步 GitHub 最新版本...
git fetch origin main
git reset --hard origin/main
if %errorlevel% neq 0 (
    echo [錯誤] git 同步失敗
    pause
    exit /b 1
)
echo [OK] 程式碼已同步

echo.
echo [2/3] 更新 Python 套件...
cd /d D:\portal\backend
py -3.11 -m pip install -r requirements.txt -q
echo [OK] 完成

echo.
echo [3/3] 重新建置前端...
cd /d D:\portal\frontend
call npm install --silent
call npm run build
if %errorlevel% neq 0 (
    echo [錯誤] 前端 build 失敗
    pause
    exit /b 1
)
echo [OK] 前端建置完成

echo.
echo ================================================
echo  更新完成！請重新啟動後端：
echo.
echo  cd D:\portal\backend
echo  py -3.11 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
echo ================================================
echo.
pause
