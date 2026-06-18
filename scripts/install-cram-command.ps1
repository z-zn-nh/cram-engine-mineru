param(
    [string]$InstallDir = "$env:USERPROFILE\.cram-engine-mineru\bin",
    [string]$Python = "py -3.13"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$cramPy = Join-Path $repoRoot "app\backend\cram.py"
$templatePath = Join-Path $PSScriptRoot "cram.cmd.template"

if (-not (Test-Path -LiteralPath $cramPy)) {
    throw "Cannot find TUI entrypoint: $cramPy"
}
if (-not (Test-Path -LiteralPath $templatePath)) {
    throw "Cannot find command template: $templatePath"
}

$template = Get-Content -Raw -LiteralPath $templatePath
$content = $template.Replace("@CRAM_PY@", $cramPy).Replace("@PYTHON@", $Python)

$windowsAppsDir = Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps"
$command_locations = @($InstallDir)
if (Test-Path -LiteralPath $windowsAppsDir) {
    $command_locations += $windowsAppsDir
}

$installedPaths = @()
foreach ($location in $command_locations) {
    New-Item -ItemType Directory -Force -Path $location | Out-Null
    $cmdPath = Join-Path $location "cram.cmd"
    [System.IO.File]::WriteAllText($cmdPath, $content, [System.Text.UTF8Encoding]::new($false))
    $installedPaths += $cmdPath
}

$currentUserPath = [Environment]::GetEnvironmentVariable("PATH", "User")
$pathParts = @()
if ($currentUserPath) {
    $pathParts = $currentUserPath -split ";"
}

$alreadyOnPath = $pathParts | Where-Object {
    $_.TrimEnd("\") -ieq $InstallDir.TrimEnd("\")
}

if (-not $alreadyOnPath) {
    $newPath = if ($currentUserPath) { "$currentUserPath;$InstallDir" } else { $InstallDir }
    [Environment]::SetEnvironmentVariable("PATH", $newPath, "User")
}

Write-Host "Installed cram command:"
$installedPaths | ForEach-Object { Write-Host "  $_" }
Write-Host "Try: cram --status"
Write-Host "If cmd still cannot find cram, reopen Windows Terminal or run: refreshenv"
