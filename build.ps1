# Build ClipTide release artifacts.
# Output in dist\:
#   ClipTide-<version>.zip          - installer/updater flavor (user data in AppData)
#   ClipTide-Portable-<version>.zip - portable flavor (user data next to the exe)
#
# Usage: powershell -ExecutionPolicy Bypass -File build.ps1

$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$pyinstaller = Join-Path $root "venv\Scripts\pyinstaller.exe"
$version = (Get-Content (Join-Path $root "data\version.txt") -TotalCount 1).Trim()

Write-Host "=== Building ClipTide $version ===" -ForegroundColor Cyan

# 1. Main app (onedir -> dist\ClipTide\)
& $pyinstaller (Join-Path $root "ClipTide.spec") --noconfirm
if ($LASTEXITCODE -ne 0) { throw "ClipTide.spec build failed" }

# 2. Updater (onefile -> dist\update.exe)
& $pyinstaller (Join-Path $root "updater.spec") --noconfirm
if ($LASTEXITCODE -ne 0) { throw "updater.spec build failed" }

$appDir = Join-Path $root "dist\ClipTide"
Copy-Item (Join-Path $root "dist\update.exe") (Join-Path $appDir "update.exe") -Force

# 3. Regular zip (consumed by the updater / installed to AppData)
$zipNormal = Join-Path $root "dist\ClipTide-$version.zip"
if (Test-Path $zipNormal) { Remove-Item $zipNormal -Force }
Compress-Archive -Path (Join-Path $appDir "*") -DestinationPath $zipNormal
Write-Host "Done: $zipNormal" -ForegroundColor Green

# 4. Portable zip: same content + portable.txt marker
$marker = Join-Path $appDir "portable.txt"
"This file makes ClipTide portable: all settings and data are stored in the 'userdata' folder next to ClipTide.exe. Delete this file to switch back to normal mode (data in AppData)." |
    Out-File -FilePath $marker -Encoding utf8

$zipPortable = Join-Path $root "dist\ClipTide-Portable-$version.zip"
if (Test-Path $zipPortable) { Remove-Item $zipPortable -Force }
Compress-Archive -Path (Join-Path $appDir "*") -DestinationPath $zipPortable
Remove-Item $marker -Force
Write-Host "Done: $zipPortable" -ForegroundColor Green

Write-Host "=== Build finished ===" -ForegroundColor Cyan
