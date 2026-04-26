@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ════════════════════════════════════════════════════════════════
::  Portal 正式環境部署腳本
::  執行前提：
::    1. 已安裝 Python 3.11
::    2. 已安裝 Node.js 20+
::    3. 已安裝 nssm（nssm.exe 在 PATH 或 C:\Windows\System32）
::    4. D:\portal\backend\.env 已設定完畢
:: ════════════════════════════════════════════════════════════════

echo.
echo  ██████╗  ██████╗ ██████╗ ████████╗ █████╗ ██╗
echo  ██╔══██╗██╔═══██╗██╔══██╗╚══██╔══╝██╔══██╗██║
echo  ██████╔╝██║   ██║██████╔╝   ██║   ███████║██║
echo  ██╔═══╝ ██║   ██║██╔══██╗   ██║   ██╔══██║██║
echo  ██║     ╚██████╔╝██║  ██║   ██║   ██║  ██║███████╗
echo  ╚═╝      ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚══════╝
echo  集團 Portal — 正式環境部署腳本
echo.

:: ── 檢查管理員權限 ────────────────────────────────────────────
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [錯誤] 請用「系統管理員身分」執行此批次檔！
    echo        對此檔案按右鍵 ^> 以系統管理員身分執行
    pause
    exit /b 1
)
echo [OK] 管理員權限確認

:: ── 確認工作目錄 ──────────────────────────────────────────────
if not exist "D:\portal\backend\app\main.py" (
    echo [錯誤] 找不到 D:\portal\backend\app\main.py
    echo        請確認程式碼已複製到 D:\portal\
    pause
    exit /b 1
)
echo [OK] 專案目錄確認：D:\portal

:: ── 確認 .env ─────────────────────────────────────────────────
if not exist "D:\portal\backend\.env" (
    echo [錯誤] 找不到 D:\portal\backend\.env
    echo        請依部署指南建立 .env 後再執行
    pause
    exit /b 1
)
echo [OK] .env 設定檔確認

:: ── 確認 Python 3.11 ──────────────────────────────────────────
py -3.11 --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [錯誤] 找不到 Python 3.11，請先安裝
    echo        https://www.python.org/downloads/release/python-3119/
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('py -3.11 --version') do echo [OK] %%v

:: ── 確認 Node.js ──────────────────────────────────────────────
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [錯誤] 找不到 Node.js，請先安裝
    echo        https://nodejs.org/
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('node --version') do echo [OK] Node.js %%v

:: ── 確認 nssm ─────────────────────────────────────────────────
nssm version >nul 2>&1
if %errorlevel% neq 0 (
    echo [錯誤] 找不到 nssm，請先安裝
    echo        https://nssm.cc/download
    echo        將 nssm.exe 複製到 C:\Windows\System32\
    pause
    exit /b 1
)
echo [OK] nssm 確認

echo.
echo ════════════════════════════════════════════════
echo  步驟 1／4：安裝 Python 套件
echo ════════════════════════════════════════════════
cd /d D:\portal\backend
py -3.11 -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [錯誤] pip install 失敗，請檢查錯誤訊息
    pause
    exit /b 1
)
echo [OK] Python 套件安裝完成

echo.
echo ════════════════════════════════════════════════
echo  步驟 2／4：初始化資料庫
echo ════════════════════════════════════════════════
if exist "D:\portal\backend\portal.db" (
    echo [跳過] portal.db 已存在，不重新初始化
    echo        若要重新初始化，請手動刪除 D:\portal\backend\portal.db
) else (
    py -3.11 init_db.py
    if %errorlevel% neq 0 (
        echo [錯誤] init_db.py 執行失敗
        pause
        exit /b 1
    )
    echo [OK] 資料庫初始化完成
)

echo.
echo ════════════════════════════════════════════════
echo  步驟 3／4：建置前端
echo ════════════════════════════════════════════════
cd /d D:\portal\frontend

echo [執行] npm install ...
call npm install
if %errorlevel% neq 0 (
    echo [錯誤] npm install 失敗
    pause
    exit /b 1
)

echo [執行] npm run build ...
call npm run build
if %errorlevel% neq 0 (
    echo [錯誤] npm run build 失敗，請檢查 TypeScript 錯誤
    pause
    exit /b 1
)
echo [OK] 前端建置完成

echo.
echo ════════════════════════════════════════════════
echo  步驟 4／4：設定並啟動 Windows 服務
echo ════════════════════════════════════════════════

:: 取得 uvicorn 路徑
for /f "tokens=*" %%p in ('py -3.11 -c "import sys,os; print(os.path.join(os.path.dirname(sys.executable), 'Scripts', 'uvicorn.exe'))"') do set UVICORN=%%p
echo [INFO] uvicorn 路徑：%UVICORN%

if not exist "%UVICORN%" (
    echo [錯誤] 找不到 uvicorn.exe：%UVICORN%
    pause
    exit /b 1
)

:: 移除舊服務（如果存在）
nssm status PortalBackend >nul 2>&1
if %errorlevel% equ 0 (
    echo [INFO] 移除舊的 PortalBackend 服務...
    nssm stop PortalBackend >nul 2>&1
    nssm remove PortalBackend confirm >nul 2>&1
)

:: 建立 log 資料夾
if not exist "D:\portal\logs" mkdir D:\portal\logs

:: 安裝新服務
echo [執行] 安裝 PortalBackend 服務...
nssm install PortalBackend "%UVICORN%"
nssm set PortalBackend AppDirectory D:\portal\backend
nssm set PortalBackend AppParameters "app.main:app --host 0.0.0.0 --port 8000 --workers 2"
nssm set PortalBackend DisplayName "Portal Backend"
nssm set PortalBackend Description "集團 Portal FastAPI 後端服務"
nssm set PortalBackend Start SERVICE_AUTO_START
nssm set PortalBackend AppStdout D:\portal\logs\portal_stdout.log
nssm set PortalBackend AppStderr D:\portal\logs\portal_stderr.log
nssm set PortalBackend AppRotateFiles 1
nssm set PortalBackend AppRotateBytes 10485760

:: 啟動服務
echo [執行] 啟動服務...
nssm start PortalBackend
if %errorlevel% neq 0 (
    echo [錯誤] 服務啟動失敗，請查看錯誤訊息
    echo        log 路徑：D:\portal\logs\portal_stderr.log
    pause
    exit /b 1
)

:: 防火牆
echo [執行] 開放防火牆 port 8000...
netsh advfirewall firewall delete rule name="Portal Port 8000" >nul 2>&1
netsh advfirewall firewall add rule name="Portal Port 8000" dir=in action=allow protocol=TCP localport=8000

echo.
echo ════════════════════════════════════════════════
echo  部署完成！
echo ════════════════════════════════════════════════
echo.
echo  服務狀態：
nssm status PortalBackend
echo.
echo  請在瀏覽器開啟：
echo  http://192.168.0.210:8000
echo.
echo  若服務異常，查看 log：
echo  D:\portal\logs\portal_stderr.log
echo.
pause
