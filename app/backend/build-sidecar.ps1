$ErrorActionPreference = "Stop"

$backendRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoAppRoot = Split-Path -Parent $backendRoot
$binariesDir = Join-Path $repoAppRoot "tauri\src-tauri\binaries"

New-Item -ItemType Directory -Force -Path $binariesDir | Out-Null

Push-Location $backendRoot
try {
    pyinstaller pyinstaller.spec --clean --noconfirm --distpath $binariesDir
}
finally {
    Pop-Location
}
