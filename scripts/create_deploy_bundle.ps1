$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$releaseDir = Join-Path $root 'release-artifacts'
$dateStamp = Get-Date -Format 'yyyyMMdd'
$defaultBundlePath = Join-Path $releaseDir "deploy_bundle_${dateStamp}.tar.gz"
$bundlePath = if ($args.Count -gt 0) { $args[0] } else { $defaultBundlePath }

if (-not (Test-Path -LiteralPath $releaseDir)) {
    New-Item -ItemType Directory -Path $releaseDir | Out-Null
}

$excludeArgs = @(
    "--exclude=.git",
    "--exclude=.github",
    "--exclude=node_modules",
    "--exclude=frontend/node_modules",
    "--exclude=frontend/dist",
    "--exclude=frontend/dev-dist",
    "--exclude=frontend/test-results",
    "--exclude=__pycache__",
    "--exclude=*.pyc",
    "--exclude=.pytest_cache",
    "--exclude=.venv",
    "--exclude=logs",
    "--exclude=output",
    "--exclude=evaluation_results",
    "--exclude=paper",
    "--exclude=paper-photo",
    "--exclude=DeepScientist",
    "--exclude=.idea",
    "--exclude=.vscode",
    "--exclude=.cursor",
    "--exclude=.claude",
    "--exclude=.zed",
    "--exclude=.zcf",
    "--exclude=docs",
    "--exclude=tests",
    "--exclude=auto-research",
    "--exclude=ui-design",
    "--exclude=doctor",
    "--exclude=*.log",
    "--exclude=*.tar",
    "--exclude=*.tar.gz",
    "--exclude=.env",
    "--exclude=.env.production",
    "--exclude=scripts",
    "--exclude=backend/data",
    "--exclude=backend/tests",
    "--exclude=backend/benchmark",
    "--exclude=frontend/.storybook",
    "--exclude=frontend/scripts",
    "--exclude=frontend/src/stories",
    "--exclude=frontend/**/*.spec.ts",
    "--exclude=frontend/tmp_utf8_test.txt"
)

$includeArgs = @(
    'Dockerfile',
    'docker-compose.prod.yml',
    'requirements-prod.txt',
    '.dockerignore',
    'backend',
    'frontend',
    'database'
)

if (Test-Path $bundlePath) {
    Remove-Item -LiteralPath $bundlePath -Force
}

Push-Location $root
try {
    & tar -czf $bundlePath @excludeArgs @includeArgs
} finally {
    Pop-Location
}

Write-Output "Created deploy bundle at $bundlePath"
