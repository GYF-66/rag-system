param(
    [switch]$SkipDoctor,
    [switch]$OpenBrowser
)

& (Join-Path $PSScriptRoot "start_deepscientist_silent.ps1") `
    -ProjectRoot (Resolve-Path (Join-Path $PSScriptRoot "..")).Path `
    -RequiredVars @("OPENAI_API_KEY", "TELEGRAM_BOT_TOKEN") `
    -SkipDoctor:$SkipDoctor `
    -OpenBrowser:$OpenBrowser
