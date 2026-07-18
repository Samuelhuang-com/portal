@echo off
chcp 65001 >nul
title Portal - DB 搬遷至 C:\Portal_Data (v1)

REM =============================================================================
REM  正式區 DB 搬離 OneDrive / 專案資料夾 → C:\Portal_Data\
REM
REM  背景（2026-07-15 與 Samuel 確認）：
REM    sync_tool.py（獨立行程）與後端 APScheduler 排程各自無鎖同時寫同一份
REM    SQLite，若 DB 又剛好在 OneDrive 同步資料夾內，OneDrive client 的檔案
REM    鎖定會疊加 SQLite 的鎖等待，更容易觸發 "database is locked"。
REM    這支腳本把正式區用到的 3 份 SQLite（portal.db / cycle-purchase.db /
REM    budget_system_v1.sqlite）統一「複製」一份到 C:\Portal_Data\，並更新
REM    .env 指向新路徑。
REM
REM  安全設計：只用 COPY，不刪除原始檔案。確認新位置運作正常幾天後，
REM  再自行手動刪除舊檔案（本腳本不會自動刪）。
REM
REM  執行前請確認：
REM    1. 已經在 D:\portal 執行過 prod-update.bat（git pull），確保程式碼
REM       是最新版（含 config.py 的 BUDGET_DB_PATH 支援）。
REM    2. 目前沒有人正在用 sync_tool.py 手動同步中。
REM
REM  執行方式：直接雙擊，或在 D:\portal 底下用 cmd 執行。
REM =============================================================================

REM -- anti-close: open new window
if not "%PROD_LAUNCHED%"=="1" (
    set PROD_LAUNCHED=1
    start "Portal DB Migration" cmd /k ""%~f0""
    exit /b
)

set PORTAL_ROOT=D:\portal
set DATA_DIR=C:\Portal_Data

echo.
echo ======================================
echo  Portal - DB 搬遷至 C:\Portal_Data
echo ======================================
echo.
echo 專案根目錄：%PORTAL_ROOT%
echo 新資料目錄：%DATA_DIR%
echo.
echo 本腳本只會「複製」現有 DB 到新位置，不會刪除原始檔案。
echo.
pause

REM ── Step 1：停止服務 ─────────────────────────────────────────────────────
echo.
echo [1/6] 停止正式區服務...
echo.

sc query PortalBackend >nul 2>&1
if not errorlevel 1 (
    echo [NSSM] 找到 PortalBackend 服務，停止中...
    net stop PortalBackend
    echo [OK] PortalBackend 服務已停止
) else (
    echo [INFO] 找不到 NSSM 服務，改用 port 8000 找行程...
    for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING"') do (
        echo [INFO] 結束 PID %%p（port 8000）...
        taskkill /PID %%p /F >nul 2>&1
    )
    echo [OK] 已嘗試結束佔用 8000 port 的行程
)

timeout /t 2 /nobreak >nul
echo.
echo ⚠ 請確認 sync_tool.py 視窗也已經關閉（若正式區主機上有開著）。
pause

REM ── Step 2：建立 C:\Portal_Data\ ─────────────────────────────────────────
echo.
echo [2/6] 建立 %DATA_DIR% ...
if not exist "%DATA_DIR%" (
    mkdir "%DATA_DIR%"
    echo [OK] 已建立 %DATA_DIR%
) else (
    echo [OK] %DATA_DIR% 已存在
)
echo.
pause

REM ── Step 3：WAL checkpoint（把 -wal 內容併回主檔，避免搬遷後資料不完整）──
echo.
echo [3/6] WAL checkpoint（若 Python 找不到會跳過，不影響後續複製）...
echo.

set PY_CMD=
py -3.12 --version >nul 2>&1
if not errorlevel 1 set PY_CMD=py -3.12

if defined PY_CMD (
    for %%F in ("%PORTAL_ROOT%\backend\portal.db" "%PORTAL_ROOT%\portal.db" "%PORTAL_ROOT%\backend\cycle-purchase.db" "%PORTAL_ROOT%\cycle-purchase.db" "%PORTAL_ROOT%\budget_system_v1.sqlite" "%PORTAL_ROOT%\backend\budget_system_v1.sqlite") do (
        if exist "%%~F" (
            echo   checkpoint: %%~F
            %PY_CMD% -c "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); c.execute('PRAGMA wal_checkpoint(FULL)'); c.close()" "%%~F"
        )
    )
    echo [OK] WAL checkpoint 完成
) else (
    echo [WARN] 找不到 py -3.12，跳過 checkpoint（服務已停止，理論上不影響資料完整性，但建議確認後再繼續）
)
echo.
pause

REM ── Step 4：複製 DB 檔案（含 -wal / -shm / -journal）───────────────────
echo.
echo [4/6] 複製 DB 檔案到 %DATA_DIR% ...
echo.

REM -- portal.db：優先找 backend\portal.db（若非 0 byte 的空樁檔），
REM    找不到／是空檔案 → 改找專案根目錄那份
set SRC_PORTAL=
set BACKEND_PORTAL_SIZE=0
if exist "%PORTAL_ROOT%\backend\portal.db" for %%A in ("%PORTAL_ROOT%\backend\portal.db") do set BACKEND_PORTAL_SIZE=%%~zA
if not "%BACKEND_PORTAL_SIZE%"=="0" set SRC_PORTAL=%PORTAL_ROOT%\backend\portal.db
if not defined SRC_PORTAL if exist "%PORTAL_ROOT%\portal.db" set SRC_PORTAL=%PORTAL_ROOT%\portal.db

if defined SRC_PORTAL (
    echo   來源：%SRC_PORTAL%
    copy /Y "%SRC_PORTAL%" "%DATA_DIR%\portal.db" >nul
    if exist "%SRC_PORTAL%-wal" copy /Y "%SRC_PORTAL%-wal" "%DATA_DIR%\portal.db-wal" >nul
    if exist "%SRC_PORTAL%-shm" copy /Y "%SRC_PORTAL%-shm" "%DATA_DIR%\portal.db-shm" >nul
    if exist "%SRC_PORTAL%-journal" copy /Y "%SRC_PORTAL%-journal" "%DATA_DIR%\portal.db-journal" >nul
    echo   [OK] portal.db 已複製 → %DATA_DIR%\portal.db
) else (
    echo   [WARN] 找不到現有 portal.db，將由程式在新位置自動建立空白 DB（請確認這是預期行為！）
)
echo.

REM -- cycle-purchase.db
set SRC_CP=
if exist "%PORTAL_ROOT%\backend\cycle-purchase.db" set SRC_CP=%PORTAL_ROOT%\backend\cycle-purchase.db
if not defined SRC_CP if exist "%PORTAL_ROOT%\cycle-purchase.db" set SRC_CP=%PORTAL_ROOT%\cycle-purchase.db

if defined SRC_CP (
    echo   來源：%SRC_CP%
    copy /Y "%SRC_CP%" "%DATA_DIR%\cycle-purchase.db" >nul
    if exist "%SRC_CP%-wal" copy /Y "%SRC_CP%-wal" "%DATA_DIR%\cycle-purchase.db-wal" >nul
    if exist "%SRC_CP%-shm" copy /Y "%SRC_CP%-shm" "%DATA_DIR%\cycle-purchase.db-shm" >nul
    echo   [OK] cycle-purchase.db 已複製 → %DATA_DIR%\cycle-purchase.db
) else (
    echo   [INFO] 找不到 cycle-purchase.db（可能尚未使用此模組，可忽略）
)
echo.

REM -- budget_system_v1.sqlite
set SRC_BUDGET=
if exist "%PORTAL_ROOT%\budget_system_v1.sqlite" set SRC_BUDGET=%PORTAL_ROOT%\budget_system_v1.sqlite
if not defined SRC_BUDGET if exist "%PORTAL_ROOT%\backend\budget_system_v1.sqlite" set SRC_BUDGET=%PORTAL_ROOT%\backend\budget_system_v1.sqlite

if defined SRC_BUDGET (
    echo   來源：%SRC_BUDGET%
    copy /Y "%SRC_BUDGET%" "%DATA_DIR%\budget_system_v1.sqlite" >nul
    if exist "%SRC_BUDGET%-wal" copy /Y "%SRC_BUDGET%-wal" "%DATA_DIR%\budget_system_v1.sqlite-wal" >nul
    if exist "%SRC_BUDGET%-shm" copy /Y "%SRC_BUDGET%-shm" "%DATA_DIR%\budget_system_v1.sqlite-shm" >nul
    echo   [OK] budget_system_v1.sqlite 已複製 → %DATA_DIR%\budget_system_v1.sqlite
) else (
    echo   [INFO] 找不到 budget_system_v1.sqlite（可能尚未使用預算模組，可忽略）
)

echo.
echo 請檢查上面每一項複製結果是否符合預期（尤其是「找不到」的警告）。
pause

REM ── Step 5：更新 .env（呼叫 _migrate_env_update.py，避免在 .bat 內硬寫 Python）──
echo.
echo [5/6] 更新 %PORTAL_ROOT%\backend\.env ...
echo.

if defined PY_CMD (
    if exist "%PORTAL_ROOT%\_migrate_env_update.py" (
        %PY_CMD% "%PORTAL_ROOT%\_migrate_env_update.py"
    ) else (
        echo [ERROR] 找不到 %PORTAL_ROOT%\_migrate_env_update.py
        echo         請確認這個檔案跟 migrate_db_to_portal_data.bat 放在同一個資料夾（D:\portal 底下），
        echo         或先執行 prod-update.bat（git pull）取得最新版。
        pause
    )
) else (
    echo [WARN] 找不到 py -3.12，無法自動更新 .env，請手動編輯 %PORTAL_ROOT%\backend\.env：
    echo   DATABASE_URL=sqlite:///C:/Portal_Data/portal.db
    echo   CYCLE_PURCHASE_DATABASE_URL=sqlite:///C:/Portal_Data/cycle-purchase.db
    echo   BUDGET_DB_PATH=C:/Portal_Data/budget_system_v1.sqlite
    pause
)
echo.
pause

REM ── Step 6：重啟服務 ─────────────────────────────────────────────────────
echo.
echo [6/6] 重啟正式區服務...
echo.

sc query PortalBackend >nul 2>&1
if not errorlevel 1 (
    net start PortalBackend
    echo [OK] PortalBackend 服務已重啟
) else (
    start "Portal Backend" cmd /k "cd /d %PORTAL_ROOT%\backend && py -3.12 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"
    echo [OK] uvicorn 已在新視窗啟動
)

echo.
echo ======================================
echo  搬遷腳本執行完畢！
echo.
echo  請務必檢查：
echo  1. 後端啟動 log 有無錯誤（尤其是 "database is locked" 或 "no such table"）
echo  2. 打開 Portal 網頁，確認資料都正常顯示（不是空的）
echo  3. 確認無誤後，觀察幾天再手動刪除 %PORTAL_ROOT% 底下的舊 DB 檔案
echo     （本腳本刻意不自動刪除，避免搬錯資料位置造成資料遺失）
echo ======================================
echo.
pause
