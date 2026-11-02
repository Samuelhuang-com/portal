@echo off
chcp 65001 >nul
title 正式區 2026-11-01 日曜料號主檔匯入（prod-update 之後執行）
setlocal
echo 請先把三支 SQL 複製到正式區的 D:\portal\sql\ ：
echo   riyo_item_check.sql、riyo_item_import.sql、riyo_item_fill.sql
echo.
if not exist D:\portal\sql\riyo_item_check.sql (echo [STOP] 找不到 D:\portal\sql\riyo_item_check.sql & pause & exit /b 1)

set PGHOST=
set PGPORT=5432
set PGUSER=
set PGDATABASE=
set /p PGHOST=週採庫 主機（PGHOST）：
set /p PGUSER=使用者（PGUSER）：
set /p PGDATABASE=資料庫名稱（PGDATABASE）：
set /p PGPASSWORD=密碼（PGPASSWORD）：
where psql >nul 2>&1 || (echo [STOP] 找不到 psql，請把 PostgreSQL 的 bin 加入 PATH。 & pause & exit /b 1)

echo [1/3] 檢查（唯讀，不寫入）...
psql -v ON_ERROR_STOP=1 -f D:\portal\sql\riyo_item_check.sql
echo 上方列出缺少的主檔。缺漏不影響匯入，但建議之後補齊。
pause

echo [2/3] 匯入（缺主檔也會匯入；只有料號代碼已存在會中止）...
psql -v ON_ERROR_STOP=1 -f D:\portal\sql\riyo_item_import.sql
if errorlevel 1 (echo [STOP] 匯入中止，未寫入任何資料。請看上方訊息。 & pause & exit /b 1)
echo 匯入完成。上方會顯示 categories 95、items 285、mappings 應有 929（缺部門的對照會略過）。
pause

echo [3/3] 之後主檔補齊時，再執行（可重複執行）：
echo   psql -v ON_ERROR_STOP=1 -f D:\portal\sql\riyo_item_fill.sql
pause
exit /b 0
