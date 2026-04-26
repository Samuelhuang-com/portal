@echo off
chcp 65001 >nul
setlocal

:: ════════════════════════════════════════════════════════════════
::  Portal 正式環境更新腳本
::  執行：以系統管理員身分執行此 .bat
::  作用：git pull → pip install → npm build → 重啟服務
:: ════════════════════════════════════════════════════════════════

echo.
echo  [Portal] 開始更新...
echo  時間：%DATE% %TIME%
echo.

:: ── 管理員權限檢查 ───────────────────────────────────────────
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [錯誤] 請用「系統管理員身分」執行！
    pause
    exit /b 1
)

:: ── 確認 git 存在 ─────────────────────────────────────────────
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [錯誤] 找不到 git，請先安裝 Git for Windows
    echo        https://git-scm.com/download/win
    pause
    exit /b 1
)

:: ── 停止服務 ──────────────────────────────────────────────────
echo [1/5] 停止後端服務...
nssm stop PortalBackend >nul 2>&1
timeout /t 2 /nobreak >nul

:: ── git pull ──────────────────────────────────────────────────
echo [2/5] 從 GitHub 拉取最新程式碼...
cd /d D:\portal
git pull origin main
if %errorlevel% neq 0 (
    echo [錯誤] git pull 失敗，請確認網路或 GitHub 設定
    nssm start PortalBackend >nul 2>&1
    pause
    exit /b 1
)
echo [OK] 程式碼已更新

:: ── pip install（只在 requirements.txt 有變動時才慢）─────────
echo [3/5] 更新 Python 套件...
cd /d D:\portal\backend
py -3.11 -m pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo [錯誤] pip install 失敗
    pause
    exit /b 1
)
echo [OK] Python 套件已更新

:: ── npm build ─────────────────────────────────────────────────
echo [4/5] 重新建置前端...
cd /d D:\portal\frontend
call npm install --silent
call npm run build
if %errorlevel% neq 0 (
    echo [錯誤] npm build 失敗，請檢查 TypeScript 錯誤
    nssm start PortalBackend >nul 2>&1
    pause
    exit /b 1
)
echo [OK] 前端建置完成

:: ── 重啟服務 ──────────────────────────────────────────────────
echo [5/5] 重啟後端服務...
nssm start PortalBackend
if %errorlevel% neq 0 (
    echo [錯誤] 服務啟動失敗，請查看：D:\portal\logs\portal_stderr.log
    pause
    exit /b 1
)

timeout /t 3 /nobreak >nul
nssm status PortalBackend

echo.
echo ════════════════════════════════════════════════
echo  更新完成！http://192.168.0.210:8000
echo ════════════════════════════════════════════════
echo.
pause
