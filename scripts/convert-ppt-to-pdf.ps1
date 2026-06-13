param(
  [Parameter(Mandatory = $true)]
  [string]$InputPath,

  [Parameter(Mandatory = $true)]
  [string]$OutputDir
)

$resolvedInput = Resolve-Path -LiteralPath $InputPath -ErrorAction Stop
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$soffice = Get-Command soffice -ErrorAction SilentlyContinue
if (-not $soffice) {
  throw "LibreOffice 'soffice' was not found. Install LibreOffice or skip PPT-to-PDF fallback."
}

& $soffice.Source --headless --convert-to pdf --outdir $OutputDir $resolvedInput.Path
exit $LASTEXITCODE
