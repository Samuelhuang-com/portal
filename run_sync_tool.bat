@echo off
chcp 65001 >nul
title Portal 同步管理工具

REM ── Python 優先順序：venv312 > venv311 > Python312 > Python311 ────────────
set TOOL=%~dp0sync_tool.py
set PYTHON=

REM 1. 正式區 venv312（prod-update.bat 安裝套件的位置）
if exist "D:\portal\backend\venv312\Scripts\python.exe" (
    set PYTHON=D:\portal\backend\venv312\Scripts\python.exe
    goto :run
)

REM 2. OneDrive 開發區 venv312
if exist "%~dp0backend\venv312\Scripts\python.exe" (
    set PYTHON=%~dp0backend\venv312\Scripts\python.exe
    goto :run
)

REM 3. Python 312 系統安裝
if exist "C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe" (
    set PYTHON=C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe
    goto :run
)

REM 4. Python 311 系統安裝
if exist "C:\Users\admin\AppData\Local\Programs\Python\Python311\python.exe" (
    set PYTHON=C:\Users\admin\AppData\Local\Programs\Python\Python311\python.exe
    goto :run
)

REM 5. py launcher 嘗試 3.12
where py >nul 2>&1 && py -3.12 --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON=py -3.12
    goto :run
)

echo [ERROR] 找不到可用的 Python 環境！
echo         請確認 D:\portal\backend\venv312 已建立，或系統已安裝 Python 3.11/3.12。
pause
exit /b 1

:run
echo 使用 Python：%PYTHON%
"%PYTHON%" "%TOOL%"
