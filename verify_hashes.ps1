<#
  verify_hashes.ps1 - pure ASCII
  Computes SHA256 of the 8 finalized files and writes them to a fresh
  log file, so Claude can compare against the known-good reference
  hashes without going through any container-side file cache.
#>
$ErrorActionPreference = 'Stop'
$PortalRoot = $PSScriptRoot
$Timestamp  = Get-Date -Format 'yyyyMMdd-HHmmss'
$LogPath    = Join-Path $PortalRoot ("_cp_verify_hashes_" + $Timestamp + ".txt")

$Files = @(
    'backend\app\core\config.py',
    'backend\.env',
    'backend\.env.example',
    'backend\app\main.py',
    'backend\app\routers\role_permissions.py',
    'frontend\src\constants\navLabels.ts',
    'frontend\src\components\Layout\MainLayout.tsx',
    'frontend\src\router\index.tsx'
)

$lines = @()
foreach ($rel in $Files) {
    $full = Join-Path $PortalRoot $rel
    if (Test-Path $full) {
        $h = (Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash
        $len = (Get-Item -LiteralPath $full).Length
        $lines += ($h + "  " + $len + "  " + $rel)
    } else {
        $lines += ("MISSING  -  " + $rel)
    }
}
$lines | Out-File -FilePath $LogPath -Encoding ascii
$lines | Write-Host
Write-Host ("Saved to " + $LogPath)
Read-Host "Press Enter to close"
