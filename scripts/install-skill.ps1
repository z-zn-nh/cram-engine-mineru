param(
  [string]$TargetRoot = "$env:USERPROFILE\.agents\skills",
  [string]$SkillName = "cram-engine-mineru"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$target = Join-Path $TargetRoot $SkillName

$itemsToCopy = @(
  "SKILL.md",
  "README.md",
  "design-spec.md",
  "AGENTS.md",
  "configs",
  "stages",
  "scripts",
  ".trae",
  ".opencode"
)

New-Item -ItemType Directory -Force -Path $TargetRoot | Out-Null

if (Test-Path -LiteralPath $target) {
  $resolved = (Resolve-Path -LiteralPath $target).Path
  $resolvedRoot = (Resolve-Path -LiteralPath $TargetRoot).Path
  if (-not $resolved.StartsWith($resolvedRoot)) {
    throw "Refusing to remove unexpected path: $resolved"
  }
  Remove-Item -LiteralPath $target -Recurse -Force
}

New-Item -ItemType Directory -Force -Path $target | Out-Null

foreach ($item in $itemsToCopy) {
  $source = Join-Path $repoRoot $item
  if (Test-Path -LiteralPath $source) {
    Copy-Item -LiteralPath $source -Destination $target -Recurse -Force
  }
}

Write-Output "Installed $SkillName to $target"
Write-Output "Start in CC desktop by uploading files and typing: qi-mo-su-cheng: course-name"
