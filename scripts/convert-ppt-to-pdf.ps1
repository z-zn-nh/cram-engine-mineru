[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$InputPath,

  [Parameter(Mandatory = $false)]
  [string]$OutputDir
)

# Manual helper to verify the PPT/PPTX -> PDF fallback that `/ingest` uses when
# MinerU cannot parse a slide deck directly. Mirrors the contract in
# app/backend/cram_app/workspace_ingest.py: it honors CRAM_LIBREOFFICE_BIN and
# otherwise falls back to `soffice` on PATH.

$ErrorActionPreference = "Stop"

$resolvedInput = Resolve-Path -LiteralPath $InputPath -ErrorAction Stop
$extension = [System.IO.Path]::GetExtension($resolvedInput.Path).ToLowerInvariant()
if ($extension -ne ".ppt" -and $extension -ne ".pptx") {
  throw "Expected a .ppt or .pptx file, got '$extension'."
}

if (-not $OutputDir) {
  $OutputDir = Split-Path -Parent $resolvedInput.Path
}
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$libreOfficeBin = $env:CRAM_LIBREOFFICE_BIN
if (-not $libreOfficeBin) {
  $libreOfficeBin = "soffice"
}

$soffice = Get-Command $libreOfficeBin -ErrorAction SilentlyContinue
if (-not $soffice) {
  throw "LibreOffice '$libreOfficeBin' was not found. Install LibreOffice, add soffice to PATH, or set CRAM_LIBREOFFICE_BIN to soffice.exe."
}

& $soffice.Source --headless --convert-to pdf --outdir $OutputDir $resolvedInput.Path
if ($LASTEXITCODE -ne 0) {
  throw "LibreOffice conversion failed with exit code $LASTEXITCODE."
}

$pdfName = [System.IO.Path]::GetFileNameWithoutExtension($resolvedInput.Path) + ".pdf"
$pdfPath = Join-Path $OutputDir $pdfName
if (-not (Test-Path -LiteralPath $pdfPath)) {
  throw "LibreOffice reported success but '$pdfPath' was not created."
}

Write-Output $pdfPath
