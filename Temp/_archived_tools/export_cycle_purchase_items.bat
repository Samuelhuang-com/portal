@echo off
setlocal

REM ===========================================================================
REM  Cycle Purchase - Export item master + item mappings
REM
REM  IMPORTANT: This file is intentionally ASCII-ONLY.
REM  cmd.exe reads a .bat using the system OEM codepage (950/Big5 on a
REM  Traditional Chinese Windows), NOT UTF-8. A UTF-8 .bat containing Chinese
REM  gets shredded into garbage that cmd then tries to run as commands.
REM  "chcp 65001" does not help - the file is already misread by then.
REM  Chinese instructions are in: export_cycle_purchase_items_README.md
REM
REM  Read-only. Does not modify the source database.
REM  Output: cycle_purchase_items_data_<timestamp>.sql
REM ===========================================================================

set "DB=C:\portal_data\cycle-purchase.db"
set "SCRIPT=%~dp0export_cycle_purchase_items.sql"

REM Timestamp via PowerShell (wmic is removed on newer Windows 11 builds)
set "STAMP="
for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"`) do set "STAMP=%%I"
if not defined STAMP set "STAMP=export"

set "OUT=%~dp0cycle_purchase_items_data_%STAMP%.sql"

echo ============================================================
echo   Cycle Purchase - export items + item mappings
echo ============================================================
echo Source DB : %DB%
echo Output    : %OUT%
echo.

if not exist "%DB%" (
    echo [ERROR] Database file not found.
    echo         Check the path against backend\.env CYCLE_PURCHASE_DATABASE_URL
    goto :end
)

if not exist "%SCRIPT%" (
    echo [ERROR] export_cycle_purchase_items.sql not found next to this .bat
    goto :end
)

where sqlite3 >nul 2>nul
if errorlevel 1 (
    echo [ERROR] sqlite3 command not found.
    echo         Download sqlite-tools-win-x64 from https://www.sqlite.org/download.html
    echo         then put sqlite3.exe in this folder, or add it to PATH.
    goto :end
)

REM Pre-flight: make sure this really is the cycle-purchase database.
REM sqlite3 silently CREATES an empty db for a wrong path, so a typo shows up
REM later as "no such table" and looks like a broken script.
set "HASTBL="
for /f "usebackq delims=" %%I in (`sqlite3 "%DB%" "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='cycle_purchase_items';"`) do set "HASTBL=%%I"
if not "%HASTBL%"=="1" (
    echo [ERROR] Table cycle_purchase_items not found in:
    echo           %DB%
    echo.
    echo         This is probably the wrong database file.
    echo         Check CYCLE_PURCHASE_DATABASE_URL in backend\.env on THIS machine,
    echo         then edit the DB= line near the top of this .bat.
    echo.
    echo         Note: D:\portal is the production server - its db path may
    echo         differ from the test environment.
    goto :end
)

sqlite3 "%DB%" < "%SCRIPT%" > "%OUT%"
if errorlevel 1 (
    echo.
    echo [ERROR] Export failed. See the message above.
    goto :end
)

for %%F in ("%OUT%") do set "SIZE=%%~zF"
echo [DONE] Exported. File size: %SIZE% bytes
echo.
echo Next steps:
echo   1. Open the output file in Notepad and read the header block.
echo      It lists the department / vendor ids this data depends on.
echo   2. Verify the TARGET database has matching departments and vendors.
echo   3. Import on the target machine with:
echo        sqlite3 "target-db-path" ".read output-file-path"
echo.
echo   (Chinese instructions: export_cycle_purchase_items_README.md)
echo.

:end
echo.
pause
endlocal
