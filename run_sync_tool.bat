@echo off
chcp 65001 >nul
title Portal 同步管理工具

REM ── 使用與 NSSM 服務相同的 Python 環境（Python311）────────────────────────
set PYTHON=C:\Users\admin\AppData\Local\Programs\Python\Python311\python.exe
set TOOL=%~dp0sync_tool.py

if not exist "%PYTHON%" (
    echo [ERROR] 找不到 Python：%PYTHON%
    pause
    exit /b 1
)

echo 使用 Python：%PYTHON%
"%PYTHON%" "%TOOL%"
