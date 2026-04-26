@echo off
chcp 65001 >nul
cd /d D:\portal

echo.
echo ==============================
echo 🏢 Portal 正式區更新工具
echo ==============================
echo.

echo [1/4] 從 GitHub 拉最新版本...
git pull origin main

echo.
echo [2/4] 安裝 / 更新後端套件...
cd /d D:\portal\backend
if exist requirements.txt (
    pip install -r requirements.txt
)

echo.
echo [3/4] 安裝 / 更新前端套件...
cd /d D:\portal\frontend
if exist package.json (
    npm install
    npm run build
)

echo.
echo [4/4] 更新完成，請重新啟動正式服務
echo.

pause