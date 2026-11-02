@echo off
chcp 65001 >nul
title 週採多公司 2026-11-01 提交與推送
setlocal EnableDelayedExpansion
cd /d C:\OneDrive\_Ragic\portal || goto :fail_nodir

if exist .git\index.lock (
    echo [INFO] 移除殘留的 .git\index.lock
    del /f .git\index.lock
)

echo [1/5] 只加入本次範圍的程式與設定（不使用 git add -A）...
git add -- .gitignore backend\app backend\alembic_cp backend\scripts frontend\src
if errorlevel 1 goto :fail

echo [2/5] 檢查已暫存的檔案是否都在允許範圍內...
set BAD=0
for /f "delims=" %%f in ('git diff --cached --name-only') do (
    set "F=%%f"
    set "OK=0"
    for %%p in (.gitignore backend/app/ backend/alembic_cp/ backend/scripts/ frontend/src/) do (
        echo !F!| findstr /b /i /c:"%%p" >nul && set OK=1
    )
    echo !F!| findstr /i /c:".sql" /c:".json" /c:"Claude" >nul && set OK=0
    if "!OK!"=="0" (
        echo [ERROR] 非預期檔案：!F!
        set BAD=1
    )
)
if "!BAD!"=="1" (
    echo [ABORT] 發現非預期檔案，已取消暫存，未提交任何東西。
    git reset -q
    goto :fail
)

for /f %%n in ('git diff --cached --name-only ^| find /c /v ""') do set CNT=%%n
echo 已暫存 !CNT! 個檔案：
git diff --cached --stat
if "!CNT!"=="0" (
    echo [INFO] 沒有需要提交的變更。
    goto :done
)

echo [3/5] 提交...
set MSG=%TEMP%\cp_msg_20261101.txt
(
    echo feat: 週採多公司隔離（cpco1-cpco4、角色權限、公司切換器、料號主檔匯入腳本）
    echo.
    echo - 後端：公司範圍依賴。可見公司由角色權限鍵 cycle_purchase_company_ch／_ou／_ho 決定（聯集）；部門歸屬只管編輯
    echo - 遷移：週採庫 cpco1-cpco4（company_code、唯一鍵、NOT NULL、OU 名稱改為日曜）
    echo - 範圍檢查：列表、單筆、POST 流程、聚合端點、週期設定、部門連結選項
    echo - 角色授權盤點腳本：scripts/cp_company_grants_plan.py（先報表、確認後套用）
    echo - 前端：公司切換器；/cycle-purchase 請求帶 co
    echo - 測試：scripts/verify_cp_company_*.py（真實 PostgreSQL）
    echo.
    echo Co-Authored-By: Claude Haiku 5.5 ^<noreply@anthropic.com^>
    echo Claude-Session: https://claude.ai/code/session_0149FCA4YUp2tqednWGjN94K
) > "%MSG%"
git commit -q -F "%MSG%"
if errorlevel 1 goto :fail

echo [4/5] 推送到 GitHub（origin main）...
git push origin main
if errorlevel 1 goto :fail

echo [5/5] 完成。最近的提交：
git log --oneline -3
goto :done

:fail
echo.
echo [FAILED] 上面有錯誤，請把畫面貼給 Claude。
pause
exit /b 1

:fail_nodir
echo [ERROR] 找不到 C:\OneDrive\_Ragic\portal
pause
exit /b 1

:done
echo.
echo 完成。接下來到正式區依序執行：prod_pre_update_20261101.bat → prod-update.bat → prod_post_update_20261101.bat
pause
exit /b 0
