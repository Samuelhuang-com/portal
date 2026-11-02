@echo off
chcp 65001 >nul
title 正式區 2026-11-01 prod-update 前置（週採庫遷移＋角色授權）
setlocal
cd /d D:\portal || (echo [ERROR] 找不到 D:\portal & pause & exit /b 1)

echo ==========================================================
echo  執行前請確認：已完成正式區「主庫」與「週採庫」的備份
echo ==========================================================
pause

echo [1/5] 拉取最新程式（與 prod-update 第 1 步相同）...
git pull origin main
if errorlevel 1 (echo [STOP] git pull 失敗，可能有未提交的本機修改，請先處理。 & pause & exit /b 1)

set PYTAG=-3.11
py -3.11 --version >nul 2>&1 || set PYTAG=-3.12
echo 使用 Python %PYTAG%

cd backend
echo [2/5] 週採庫遷移（升到 cpco4）。上方會顯示各表 company_code NULL 統計。
py %PYTAG% -m alembic -c alembic_cp.ini upgrade head
if errorlevel 1 (echo [STOP] 週採庫遷移失敗。請先處理上方錯誤，不要繼續。 & pause & exit /b 1)
py %PYTAG% -m alembic -c alembic_cp.ini current

echo [3/5] 角色授權盤點（唯讀，不寫入）...
py %PYTAG% scripts\cp_company_grants_plan.py report
if errorlevel 1 (echo [STOP] 盤點失敗。 & pause & exit /b 1)
notepad cp_company_grants_proposal.json
echo 請確認每個角色的 suggested_codes。需要修改的話，直接在記事本改完存檔。
pause

echo [4/5] 套用角色授權（乾跑，不寫入）...
py %PYTAG% scripts\cp_company_grants_plan.py apply cp_company_grants_proposal.json
echo 上方是預計的變更。確認無誤後按任意鍵寫入。
pause
py %PYTAG% scripts\cp_company_grants_plan.py apply cp_company_grants_proposal.json --yes
if errorlevel 1 (echo [STOP] 寫入授權失敗。 & pause & exit /b 1)

echo [5/5] 完成。現在執行 prod-update.bat（它會重啟後端，新權限即生效）。
pause
exit /b 0
