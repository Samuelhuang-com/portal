<#
  finalize_cycle_purchase_edits.ps1  (v3 - pure ASCII, no non-English characters)
  ------------------------------------------------------------------
  Purpose: finish applying the "Cycle Purchase" Phase 1 wiring edits.

  Background: 8 files were already written into the correct project
  folders under temp names (prefixed _cptmp_), with content verified
  byte-for-byte via SHA256 against the reviewed originals. This script
  performs the last step: rename each temp file over the real target
  file (with a timestamped backup of the original first).

  Why this version is pure ASCII: the previous version (v2) used
  Traditional Chinese text in comments/output, and produced no visible
  output or log file at all when run - the most likely cause is that
  Windows PowerShell 5.1 misread the UTF-8 file using the system's
  local codepage, corrupting a multi-byte character into something
  that broke the script parser before a single line could execute.
  Removing all non-ASCII bytes from the file removes that risk
  entirely, regardless of the system's codepage/locale settings.

  How to use:
    1. Save this file to C:\OneDrive\_Ragic\portal\ (same folder level
       as backend and frontend).
    2. Right-click it -> "Run with PowerShell".
    3. It will pause at the end and wait for Enter before closing.
    4. A log file named _cp_finalize_log_<timestamp>.txt will be
       created in the same folder - please send that file back,
       regardless of what you see on screen.
#>

$ErrorActionPreference = 'Stop'
$PortalRoot = $PSScriptRoot
$Timestamp  = Get-Date -Format 'yyyyMMdd-HHmmss'
$LogPath    = Join-Path $PortalRoot ("_cp_finalize_log_" + $Timestamp + ".txt")

Start-Transcript -Path $LogPath | Out-Null

try {
    # temp file relative path -> target relative path
    $Mapping = [ordered]@{
        'backend\app\core\_cptmp_config.py'                    = 'backend\app\core\config.py'
        'backend\_cptmp_env'                                   = 'backend\.env'
        'backend\_cptmp_env_example'                           = 'backend\.env.example'
        'backend\app\_cptmp_main.py'                           = 'backend\app\main.py'
        'backend\app\routers\_cptmp_role_permissions.py'       = 'backend\app\routers\role_permissions.py'
        'frontend\src\constants\_cptmp_navLabels.ts'           = 'frontend\src\constants\navLabels.ts'
        'frontend\src\components\Layout\_cptmp_MainLayout.tsx' = 'frontend\src\components\Layout\MainLayout.tsx'
        'frontend\src\router\_cptmp_index.tsx'                 = 'frontend\src\router\index.tsx'
    }

    Write-Host "===================================================="
    Write-Host " Cycle Purchase Phase 1 - Finalize (temp -> real file)"
    Write-Host " Portal root: $PortalRoot"
    Write-Host " Log file:    $LogPath"
    Write-Host "===================================================="
    Write-Host ""

    $results = @()

    foreach ($relSrc in $Mapping.Keys) {
        $srcPath  = Join-Path $PortalRoot $relSrc
        $relDest  = $Mapping[$relSrc]
        $destPath = Join-Path $PortalRoot $relDest

        Write-Host ("---- " + $relDest + " ----")

        if (-not (Test-Path $srcPath)) {
            Write-Host ("  [SKIP] temp file not found: " + $srcPath)
            $results += [pscustomobject]@{ File = $relDest; Status = 'SKIP (no temp file)' }
            continue
        }

        if (Test-Path $destPath) {
            $backupPath = $destPath + ".bak-" + $Timestamp
            Copy-Item -LiteralPath $destPath -Destination $backupPath -Force
            Write-Host ("  Backed up existing file -> " + $backupPath)
        } else {
            Write-Host "  (destination did not exist, no backup needed)"
        }

        Copy-Item -LiteralPath $srcPath -Destination $destPath -Force

        $srcHash  = (Get-FileHash -LiteralPath $srcPath  -Algorithm SHA256).Hash
        $destHash = (Get-FileHash -LiteralPath $destPath -Algorithm SHA256).Hash

        if ($srcHash -eq $destHash) {
            Write-Host "  Applied OK, SHA256 match."
            Remove-Item -LiteralPath $srcPath -Force
            Write-Host "  Removed temp file."
            $results += [pscustomobject]@{ File = $relDest; Status = 'OK' }
        } else {
            Write-Host "  [WARNING] SHA256 mismatch! Temp file kept, please report to Claude."
            Write-Host ("    src  hash: " + $srcHash)
            Write-Host ("    dest hash: " + $destHash)
            $results += [pscustomobject]@{ File = $relDest; Status = 'MISMATCH (kept temp file)' }
        }
        Write-Host ""
    }

    Write-Host "===================================================="
    Write-Host " Summary"
    Write-Host "===================================================="
    $results | Format-Table -AutoSize | Out-String | Write-Host

    Write-Host ""
    Write-Host "Next steps:"
    Write-Host "  1. Restart backend:  cd backend; uvicorn app.main:app --reload --port 8000"
    Write-Host "  2. Restart frontend: cd frontend; npm run dev"
    Write-Host "  3. Check that C:\portal_data\cycle-purchase.db was created with 5 new tables."
    Write-Host "  4. Go to System Settings -> Role Management -> Permissions, find the"
    Write-Host "     Cycle Purchase permission group, grant it to your role, save, refresh."
    Write-Host ""
}
catch {
    Write-Host ""
    Write-Host ("[SCRIPT ERROR] " + $_.Exception.Message)
    Write-Host $_.ScriptStackTrace
}
finally {
    Stop-Transcript | Out-Null
    Write-Host ""
    Write-Host ("Log saved to: " + $LogPath)
    Write-Host "Please send that log file to Claude."
    Read-Host "Press Enter to close this window"
}
