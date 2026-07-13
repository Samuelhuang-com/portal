<#
  finalize_cycle_purchase_edits.ps1
  ------------------------------------------------------------------
  用途：完成「週採（週期採購）」Phase 1 的最後一步。

  背景：我已經透過裝置連線工具，把 8 個修改好的檔案「以暫存檔名」
        寫入您專案裡對應的資料夾了（檔名前面多了 _cptmp_ 前綴），
        內容已經逐一用 SHA256 核對過，確定跟我驗證過的版本完全一致。
        現在只差最後一步：把這 8 個暫存檔改名蓋掉原本的檔案。

        因為裝置上另一個可以直接執行指令的工具這次沒有啟動成功，
        所以這最後一步麻煩您在本機用這支 PowerShell 腳本完成 ——
        它做的事情很單純：備份原檔 → 用暫存檔覆蓋 → 用 SHA256 驗證。

  使用方式：
    1. 把這支 .ps1 檔案存到 C:\OneDrive\_Ragic\portal\ 這個資料夾底下
       （跟 backend、frontend 同一層）。
    2. 對它按右鍵 →「使用 PowerShell 執行」
       （或在 PowerShell 視窗 cd 進去後執行 .\finalize_cycle_purchase_edits.ps1）。
    3. 不需要另外下載或搬動任何檔案 —— 暫存檔已經在正確的資料夾裡了。

  這支程式會做什麼：
    - 對下面 8 組「暫存檔 -> 目標檔」，先把目標檔（如果存在）
      備份成 <檔名>.bak-YYYYMMDD-HHMMSS。
    - 用暫存檔覆蓋目標檔，然後刪除暫存檔。
    - 用 SHA256 比對目標檔跟暫存檔內容是否一致，畫面上顯示 OK / 不一致。
    - 只會動這 8 組檔案，不會碰專案裡任何其他東西。

  如果畫面上出現任何「不一致」或紅字錯誤，請把整段輸出複製給 Claude，
  不要自行猜測原因或重試。
#>

$ErrorActionPreference = 'Stop'
$PortalRoot = $PSScriptRoot
$Timestamp  = Get-Date -Format 'yyyyMMdd-HHmmss'

# 暫存檔相對路徑 -> 目標相對路徑
$Mapping = [ordered]@{
    'backend\app\core\_cptmp_config.py'                          = 'backend\app\core\config.py'
    'backend\_cptmp_env'                                         = 'backend\.env'
    'backend\_cptmp_env_example'                                 = 'backend\.env.example'
    'backend\app\_cptmp_main.py'                                 = 'backend\app\main.py'
    'backend\app\routers\_cptmp_role_permissions.py'             = 'backend\app\routers\role_permissions.py'
    'frontend\src\constants\_cptmp_navLabels.ts'                 = 'frontend\src\constants\navLabels.ts'
    'frontend\src\components\Layout\_cptmp_MainLayout.tsx'       = 'frontend\src\components\Layout\MainLayout.tsx'
    'frontend\src\router\_cptmp_index.tsx'                       = 'frontend\src\router\index.tsx'
}

Write-Host "===================================================="
Write-Host " 週採 Phase 1 — 最終套用（暫存檔 -> 正式檔）"
Write-Host " 專案根目錄: $PortalRoot"
Write-Host "===================================================="
Write-Host ""

$results = @()

foreach ($relSrc in $Mapping.Keys) {
    $srcPath  = Join-Path $PortalRoot $relSrc
    $relDest  = $Mapping[$relSrc]
    $destPath = Join-Path $PortalRoot $relDest

    Write-Host "---- $relDest ----"

    if (-not (Test-Path $srcPath)) {
        Write-Host "  [跳過] 找不到暫存檔: $srcPath" -ForegroundColor Yellow
        Write-Host "  （這代表這個檔案可能已經套用過了，或是尚未由 Claude 寫入）"
        $results += [pscustomobject]@{ File = $relDest; Status = '跳過（無暫存檔）' }
        continue
    }

    if (Test-Path $destPath) {
        $backupPath = "$destPath.bak-$Timestamp"
        Copy-Item -LiteralPath $destPath -Destination $backupPath -Force
        Write-Host "  已備份原檔 -> $backupPath"
    } else {
        Write-Host "  (目標檔案原本不存在，略過備份)"
    }

    Copy-Item -LiteralPath $srcPath -Destination $destPath -Force

    $srcHash  = (Get-FileHash -LiteralPath $srcPath  -Algorithm SHA256).Hash
    $destHash = (Get-FileHash -LiteralPath $destPath -Algorithm SHA256).Hash

    if ($srcHash -eq $destHash) {
        Write-Host "  套用完成，SHA256 一致 (OK)" -ForegroundColor Green
        Remove-Item -LiteralPath $srcPath -Force
        Write-Host "  已刪除暫存檔"
        $results += [pscustomobject]@{ File = $relDest; Status = 'OK' }
    } else {
        Write-Host "  [警告] SHA256 不一致！暫存檔先保留，請回報給 Claude。" -ForegroundColor Red
        Write-Host "    暫存檔 hash: $srcHash"
        Write-Host "    目標檔 hash: $destHash"
        $results += [pscustomobject]@{ File = $relDest; Status = '不一致（需回報，暫存檔已保留）' }
    }
    Write-Host ""
}

Write-Host "===================================================="
Write-Host " 執行結果彙總"
Write-Host "===================================================="
$results | Format-Table -AutoSize

Write-Host ""
Write-Host "接下來請重啟後端與前端開發伺服器，讓變更生效："
Write-Host "  後端: cd backend; uvicorn app.main:app --reload --port 8000"
Write-Host "  前端: cd frontend; npm run dev"
Write-Host ""
Write-Host "重啟後端後，請確認 C:\portal_data\cycle-purchase.db 有被建立、"
Write-Host "並用 sqlite3 或 DB Browser 檢查裡面有 5 張以 cycle_purchase_ 開頭的資料表。"
Write-Host ""
Write-Host "登入 Portal 後，請到「系統設定 -> 角色管理 -> 權限設定」，"
Write-Host "找到「週期採購」這個分組，勾選您角色需要的權限（至少勾 週期採購管理），"
Write-Host "存檔後重新整理頁面，左側選單應該就會出現「週採」。"
Write-Host ""
Write-Host "如果畫面上有任何『不一致』或紅字錯誤，請把整段輸出複製貼給 Claude。"