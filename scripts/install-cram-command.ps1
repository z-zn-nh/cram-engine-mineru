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

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

$cmdPath = Join-Path $InstallDir "cram.cmd"
$template = Get-Content -Raw -LiteralPath $templatePath
$content = $template.Replace("@CRAM_PY@", $cramPy).Replace("@PYTHON@", $Python)
[System.IO.File]::WriteAllText($cmdPath, $content, [System.Text.UTF8Encoding]::new($false))

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

Write-Host "Installed cram command: $cmdPath"
Write-Host "If this is your first install, reopen cmd/PowerShell before running: cram"
