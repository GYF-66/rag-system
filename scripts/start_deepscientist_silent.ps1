<#
.SYNOPSIS
Starts DeepScientist in the background without opening the TUI window.

.DESCRIPTION
Reusable silent launcher for DeepScientist projects. It loads environment variables
from a project-local `.env`, optionally runs `ds --here doctor`, then starts the
managed daemon in a hidden PowerShell process.

.PARAMETER ProjectRoot
Absolute or relative path to the project root. Defaults to the parent of `scripts/`.

.PARAMETER EnvFile
Optional explicit `.env` file path. Defaults to `<ProjectRoot>/.env`.

.PARAMETER RequiredVars
Environment variables that must exist before launch.

.PARAMETER SkipDoctor
Skips `ds --here doctor` before starting the daemon.

.PARAMETER OpenBrowser
Opens `http://127.0.0.1:20999` after the silent launch request.

.PARAMETER LogFile
Optional log file path for the hidden bootstrap process.

.PARAMETER LaunchArgs
Arguments forwarded to `ds`. The default is `--here --daemon-only --no-browser --yolo true`.

.EXAMPLE
.\scripts\start_deepscientist_silent.ps1 -RequiredVars @("OPENAI_API_KEY")

.EXAMPLE
.\scripts\start_deepscientist_silent.ps1 -ProjectRoot "D:\my-project" -RequiredVars @("OPENAI_API_KEY","TELEGRAM_BOT_TOKEN") -OpenBrowser
#>
param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$EnvFile = "",
    [string[]]$RequiredVars = @("OPENAI_API_KEY"),
    [switch]$SkipDoctor,
    [switch]$OpenBrowser,
    [string]$LogFile = "",
    [string[]]$LaunchArgs = @("--here", "--daemon-only", "--no-browser", "--yolo", "true")
)

$ErrorActionPreference = "Stop"

function Get-DeepScientistHome {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root
    )

    $defaultHome = Join-Path $Root "DeepScientist"
    if (Test-Path -LiteralPath $defaultHome) {
        return (Resolve-Path -LiteralPath $defaultHome).Path
    }

    throw "Missing DeepScientist home under project root: $defaultHome"
}

function Import-DotEnv {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    Get-Content -LiteralPath $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            return
        }

        $parts = $line -split "=", 2
        if ($parts.Count -ne 2) {
            return
        }

        [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
    }
}

function Get-DaemonState {
    param(
        [Parameter(Mandatory = $true)]
        [string]$DeepScientistHome
    )

    $daemonFile = Join-Path $DeepScientistHome "runtime\daemon.json"
    if (-not (Test-Path -LiteralPath $daemonFile)) {
        return $null
    }

    try {
        return Get-Content -LiteralPath $daemonFile -Raw | ConvertFrom-Json
    } catch {
        return $null
    }
}

function Test-DaemonState {
    param(
        [Parameter(Mandatory = $true)]
        $State,
        [Parameter(Mandatory = $true)]
        [string]$ExpectedHome
    )

    if (-not $State.pid) {
        return $false
    }

    try {
        $process = Get-Process -Id ([int]$State.pid) -ErrorAction Stop
    } catch {
        return $false
    }

    if (-not $process) {
        return $false
    }

    try {
        $commandLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($State.pid)" -ErrorAction Stop).CommandLine
    } catch {
        $commandLine = ""
    }

    if (-not [string]::IsNullOrWhiteSpace($commandLine)) {
        $normalizedCommandLine = $commandLine.Replace("/", "\")
        $normalizedExpectedHome = $ExpectedHome.Replace("/", "\")
        if ($normalizedCommandLine -like "*$normalizedExpectedHome*" -and $normalizedCommandLine -like "* deepscientist.cli *daemon*") {
            return $true
        }
    }

    return $false
}

function Resolve-DsCommand {
    $dsCommand = Get-Command ds -ErrorAction SilentlyContinue
    if ($dsCommand) {
        return $dsCommand.Source
    }

    $fallback = "D:/DeepScientist/bin/ds.js"
    if (Test-Path -LiteralPath $fallback) {
        return $fallback
    }

    throw "Missing DeepScientist launcher. Expected either 'ds' on PATH or D:/DeepScientist/bin/ds.js"
}

if (-not $EnvFile) {
    $EnvFile = Join-Path $ProjectRoot ".env"
}

if (-not (Test-Path -LiteralPath $EnvFile)) {
    throw "Missing .env file: $EnvFile"
}

$resolvedProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$resolvedEnvFile = (Resolve-Path -LiteralPath $EnvFile).Path
$deepScientistHome = Get-DeepScientistHome -Root $resolvedProjectRoot
$dsLauncher = Resolve-DsCommand

if (-not $LogFile) {
    $LogDir = Join-Path $deepScientistHome "logs"
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
    $LogFile = Join-Path $LogDir "silent-launch.log"
}

Import-DotEnv -Path $resolvedEnvFile

$missingVars = @($RequiredVars | Where-Object {
    [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($_, "Process"))
})
if ($missingVars.Count -gt 0) {
    throw "Missing required environment variables: $($missingVars -join ', '). Update $resolvedEnvFile and try again."
}

$existingDaemon = Get-DaemonState -DeepScientistHome $deepScientistHome
if ($existingDaemon -and (Test-DaemonState -State $existingDaemon -ExpectedHome $deepScientistHome)) {
    Write-Host "DeepScientist is already running at $($existingDaemon.url) (PID $($existingDaemon.pid))"
    exit 0
}

if (-not $SkipDoctor) {
    if ($dsLauncher -like "*.js") {
        & node $dsLauncher --here doctor
    } else {
        & $dsLauncher --here doctor
    }
    if ($LASTEXITCODE -ne 0) {
        throw "DeepScientist doctor failed."
    }
}

$bootstrapScript = @"
`$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath '$($resolvedProjectRoot.Replace("'", "''"))'
'[' + (Get-Date).ToString('s') + '] silent bootstrap started' | Out-File -LiteralPath '$($LogFile.Replace("'", "''"))' -Append -Encoding utf8
Get-Content -LiteralPath '$($resolvedEnvFile.Replace("'", "''"))' | ForEach-Object {
    `$line = `$_.Trim()
    if (-not `$line -or `$line.StartsWith('#')) { return }
    `$parts = `$line -split '=', 2
    if (`$parts.Count -ne 2) { return }
    [Environment]::SetEnvironmentVariable(`$parts[0].Trim(), `$parts[1].Trim(), 'Process')
}
if ('$($dsLauncher.Replace("'", "''"))' -like '*.js') {
    & node '$($dsLauncher.Replace("'", "''"))' $($LaunchArgs -join ' ') *>> '$($LogFile.Replace("'", "''"))'
} else {
    & '$($dsLauncher.Replace("'", "''"))' $($LaunchArgs -join ' ') *>> '$($LogFile.Replace("'", "''"))'
}
'[' + (Get-Date).ToString('s') + '] silent bootstrap finished exit=' + `$LASTEXITCODE | Out-File -LiteralPath '$($LogFile.Replace("'", "''"))' -Append -Encoding utf8
"@

$encodedCommand = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($bootstrapScript))

Start-Process -FilePath "powershell.exe" `
    -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", $encodedCommand) `
    -WorkingDirectory $resolvedProjectRoot `
    -WindowStyle Hidden | Out-Null

Start-Sleep -Seconds 3

if ($OpenBrowser) {
    Start-Process "http://127.0.0.1:20999" | Out-Null
}

Write-Host "DeepScientist silent start requested for $resolvedProjectRoot"
