# Build ClipTide release artifacts.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File build.ps1              # onefile (по умолчанию)
#   powershell -ExecutionPolicy Bypass -File build.ps1 -Mode onedir # папка с _internal
#
# Output in dist\:
#   ClipTide.exe                    - onefile: приложение целиком, один файл
#   ClipTide-<version>.zip          - обычная поставка (данные в AppData)
#   ClipTide-Portable-<version>.zip - portable (данные рядом с exe)
#
# Отдельного update.exe больше нет: приложение не скачивает обновления, а лишь
# сообщает о новой версии и открывает страницу релизов. Zip при этом нужен —
# по нему обновляются те, кто ещё сидит на 1.7.x со старым апдейтером, и он же
# несёт portable.txt.
#
# Интерфейс работает на Qt (PySide6), поэтому Edge WebView2 Runtime
# на машине пользователя больше не требуется.

param(
    [ValidateSet('onefile', 'onedir')]
    [string]$Mode = 'onefile'
)

$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$pyinstaller = Join-Path $root "venv\Scripts\pyinstaller.exe"
$version = (Get-Content (Join-Path $root "data\version.txt") -TotalCount 1).Trim()
$distDir = Join-Path $root "dist"

$env:CLIPTIDE_BUILD = $Mode

Write-Host "=== Building ClipTide $version ($Mode) ===" -ForegroundColor Cyan

& $pyinstaller (Join-Path $root "ClipTide.spec") --noconfirm
if ($LASTEXITCODE -ne 0) { throw "ClipTide.spec build failed" }

# Что кладём в архив. onedir: PyInstaller уже собрал dist\ClipTide\.
# onefile: единственный exe уводим в отдельную папку, иначе Compress-Archive
# утащит в архив всё содержимое dist\, включая прошлые сборки.
if ($Mode -eq 'onedir') {
    $stage = Join-Path $distDir "ClipTide"
} else {
    $stage = Join-Path $distDir "package"
    if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
    New-Item -ItemType Directory -Path $stage | Out-Null
    Copy-Item (Join-Path $distDir "ClipTide.exe") $stage -Force
}

$zipNormal = Join-Path $distDir "ClipTide-$version.zip"
if (Test-Path $zipNormal) { Remove-Item $zipNormal -Force }
Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $zipNormal
Write-Host "Done: $zipNormal" -ForegroundColor Green

# Portable: то же самое плюс маркер, переключающий хранение данных
$marker = Join-Path $stage "portable.txt"
"This file makes ClipTide portable: all settings and data are stored in the 'userdata' folder next to ClipTide.exe. Delete this file to switch back to normal mode (data in AppData)." |
    Out-File -FilePath $marker -Encoding utf8

$zipPortable = Join-Path $distDir "ClipTide-Portable-$version.zip"
if (Test-Path $zipPortable) { Remove-Item $zipPortable -Force }
Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $zipPortable
Remove-Item $marker -Force
Write-Host "Done: $zipPortable" -ForegroundColor Green

if ($Mode -eq 'onefile') {
    $single = Join-Path $distDir "ClipTide.exe"
    $sizeMb = [math]::Round((Get-Item $single).Length / 1MB, 1)
    Write-Host "Single file: $single ($sizeMb MB)" -ForegroundColor Green
}

Write-Host "=== Build finished ===" -ForegroundColor Cyan
