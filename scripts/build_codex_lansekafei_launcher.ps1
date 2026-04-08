$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$sourcePath = Join-Path $projectRoot "scripts\codex_lansekafei_launcher\Program.cs"
$outputDir = Join-Path $projectRoot "scripts\codex_lansekafei_launcher\bin\Release\net8.0"
$outputPath = Join-Path $outputDir "codex_lansekafei_launcher.exe"

if (-not (Test-Path -LiteralPath $sourcePath)) {
    throw "Missing source file: $sourcePath"
}

New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
$code = Get-Content -LiteralPath $sourcePath -Raw
Add-Type -TypeDefinition $code -Language CSharp -OutputAssembly $outputPath -OutputType ConsoleApplication
Write-Host "Built launcher: $outputPath"
