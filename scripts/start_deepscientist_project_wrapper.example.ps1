param(
    [switch]$SkipDoctor,
    [switch]$OpenBrowser
)

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$launcher = Join-Path $PSScriptRoot "start_deepscientist_silent.ps1"

& $launcher `
    -ProjectRoot $projectRoot `
    -RequiredVars @(
        "OPENAI_API_KEY"
    ) `
    -SkipDoctor:$SkipDoctor `
    -OpenBrowser:$OpenBrowser
