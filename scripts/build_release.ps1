param(
    [switch]$Clean = $true
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$WorkPath = Join-Path $ProjectRoot '.pyi_build'
$DistPath = Join-Path $ProjectRoot 'release'
$OutputDir = Join-Path $DistPath 'NeteaseResourcepackManager'

if ($Clean) {
    if (Test-Path $WorkPath) { Remove-Item -Recurse -Force $WorkPath }
    if (Test-Path $DistPath) { Remove-Item -Recurse -Force $DistPath }
}

python -m PyInstaller --noconfirm --clean --workpath $WorkPath --distpath $DistPath NeteaseResourcepackManager.spec

if (-not (Test-Path (Join-Path $OutputDir 'NeteaseResourcepackManager.exe'))) {
    throw '打包失败：未找到发布 exe。'
}

Write-Output "打包完成：$OutputDir"
Write-Output '请运行 release\NeteaseResourcepackManager\NeteaseResourcepackManager.exe'
