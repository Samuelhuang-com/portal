@echo off
chcp 65001 >nul
REM =============================================================================
REM  Portal 服務主控台 - 系統管理員身分啟動器
REM
REM  背景（2026-07-18）：正式區 Backend 由 NSSM 服務（PortalBackend）常駐管理，
REM  portal_console.py 偵測到 NSSM 服務時會改用 `net start`/`net stop` 控制服務，
REM  但這兩個指令需要系統管理員權限。直接用一般權限雙擊 portal_console.py（或
REM  `python portal_console.py`）在按 Stop/Start 時會遇到「系統發生 5 錯誤，
REM  存取被拒」。
REM
REM  用法：直接雙擊這支 .bat（不要用滑鼠右鍵「以系統管理員身分執行」，這支
REM  腳本自己會判斷、自己跳 UAC 確認視窗）。
REM
REM  開發／測試機也可以用這支啟動，沒有 NSSM 服務時完全不受影響（net 相關
REM  程式碼路徑根本不會被觸發）。
REM =============================================================================

REM -- 檢查目前是否已經是系統管理員權限（net session 只有 admin 能成功執行）
net session >nul 2>&1
if %errorlevel% == 0 (
    cd /d "%~dp0"
    py -3.12 portal_console.py
    if errorlevel 1 python portal_console.py
) else (
    REM -- 不是系統管理員權限：用 PowerShell 提權，重新執行自己一次
    echo [INFO] 需要系統管理員權限才能控制 Windows 服務，準備跳出 UAC 確認視窗...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
)
