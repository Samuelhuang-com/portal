@echo off
chcp 65001 >nul
cd /d C:\OneDrive\_Ragic\portal

echo.
echo ==============================
echo 🚀 Portal GitHub 同步工具
echo ==============================
echo.

echo [1/5] 檢查 Git 狀態...
git status

echo.
set /p msg=請輸入本次 commit 訊息：

if "%msg%"=="" (
    set msg=update portal
)

echo.
echo [2/5] 加入變更檔案...
git add .

echo.
echo [3/5] 建立 Commit...
git commit -m "%msg%"

echo.
echo [4/5] Push 到 GitHub...
git push origin main

echo.
echo [5/5] 最終狀態檢查...
git status

echo.
echo ==============================
echo ✅ GitHub 同步完成
echo ==============================
pause