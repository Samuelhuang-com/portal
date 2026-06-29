@echo off
title Portal - Stop Services
echo ============================================
echo  Stopping Portal Services...
echo ============================================
echo.

REM -- 關閉標題為 "Backend PROD" 的 cmd 視窗
taskkill /FI "WINDOWTITLE eq Backend PROD" /F >nul 2>&1

REM -- 關閉標題為 "Frontend PROD" 的 cmd 視窗
taskkill /FI "WINDOWTITLE eq Frontend PROD" /F >nul 2>&1

REM -- 強制結束所有 uvicorn 程序
wmic process where "commandline like '%%uvicorn%%'" delete >nul 2>&1

REM -- 強制結束所有 vite preview 程序
wmic process where "commandline like '%%vite%%preview%%'" delete >nul 2>&1

echo [OK] Backend stopped.
echo [OK] Frontend stopped.
echo.
echo ============================================
echo  Done. Portal services stopped.
echo ============================================
echo.
pause
