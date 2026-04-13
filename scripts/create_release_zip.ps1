$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.IO.Compression.FileSystem

$root = Split-Path -Parent $PSScriptRoot
$releaseDir = Join-Path $root 'release-artifacts'
$dateStamp = Get-Date -Format 'yyyyMMdd'
$defaultBundlePath = Join-Path $releaseDir "rag-system_${dateStamp}_no-venv.zip"
$bundlePath = if ($args.Count -gt 0) { $args[0] } else { $defaultBundlePath }

$bundlePath = [System.IO.Path]::GetFullPath($bundlePath)
$bundleDir = Split-Path -Parent $bundlePath

$excludeDirectoryNames = @(
    '.git',
    '.github',
    '.venv',
    'venv',
    'env',
    'ENV',
    'node_modules',
    'dist',
    'dev-dist',
    'test-results',
    '.pytest_cache',
    '__pycache__',
    'logs',
    'output',
    'evaluation_results',
    'paper',
    'paper-photo',
    'DeepScientist',
    '.idea',
    '.vscode',
    '.cursor',
    '.claude',
    '.zed',
    '.zcf',
    'auto-research',
    'ui-design',
    'cache',
    '.deploy_staging_debug',
    'release-artifacts'
)

$excludeFileNames = @(
    '.env',
    '.env.production',
    'deploy_bundle.tar.gz',
    'doctor',
    'start-test.log',
    'dotnet-start-test.log'
)

$excludeRelativePathPatterns = @(
    'backend/data',
    'backend/data/*',
    'backend/tests',
    'backend/tests/*',
    'backend/benchmark',
    'backend/benchmark/*',
    'frontend/.storybook',
    'frontend/.storybook/*',
    'frontend/scripts',
    'frontend/scripts/*',
    'frontend/src/stories',
    'frontend/src/stories/*',
    'database/archive',
    'database/archive/*',
    'database/chroma_db',
    'database/chroma_db/*',
    'database/*.backup',
    'database/*.pre_enhance_backup'
)

$includePaths = @(
    '.dockerignore',
    '.env.example',
    '.env.production.example',
    'Dockerfile',
    'README.md',
    'docker-compose.yml',
    'docker-compose.prod.yml',
    'requirements.txt',
    'requirements-dev.txt',
    'requirements-prod.txt',
    'package.json',
    'package-lock.json',
    'backend',
    'database',
    'docs/deploy',
    'frontend'
)

function Test-ShouldExclude {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RelativePath,
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [bool]$IsDirectory
    )

    $normalizedPath = $RelativePath.Replace('\', '/')

    if ($excludeFileNames -contains $Name) {
        return $true
    }

    foreach ($pattern in $excludeRelativePathPatterns) {
        if ($normalizedPath -like $pattern) {
            return $true
        }
    }

    if ($normalizedPath -like '*.tar' -or $normalizedPath -like '*.tar.gz' -or $normalizedPath -like '*.zip') {
        return $true
    }

    if ($normalizedPath -like '*.log' -or $normalizedPath -like '*.pyc') {
        return $true
    }

    if ($normalizedPath -like 'frontend/src/*.spec.ts' -or $normalizedPath -like 'frontend/src/**/*.spec.ts') {
        return $true
    }

    if ($normalizedPath -eq 'frontend/tmp_utf8_test.txt') {
        return $true
    }

    if ($IsDirectory -and $excludeDirectoryNames -contains $Name) {
        return $true
    }

    return $false
}

function Copy-IncludedPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SourcePath,
        [Parameter(Mandatory = $true)]
        [string]$RelativePath,
        [Parameter(Mandatory = $true)]
        [string]$StageRoot
    )

    $item = Get-Item -LiteralPath $SourcePath
    $destinationPath = Join-Path $StageRoot $RelativePath

    if ($item.PSIsContainer) {
        if (-not (Test-Path -LiteralPath $destinationPath)) {
            New-Item -ItemType Directory -Path $destinationPath | Out-Null
        }

        Get-ChildItem -LiteralPath $SourcePath -Force | ForEach-Object {
            $childRelativePath = if ([string]::IsNullOrEmpty($RelativePath)) {
                $_.Name
            } else {
                Join-Path $RelativePath $_.Name
            }

            if (Test-ShouldExclude -RelativePath $childRelativePath -Name $_.Name -IsDirectory $_.PSIsContainer) {
                return
            }

            Copy-IncludedPath -SourcePath $_.FullName -RelativePath $childRelativePath -StageRoot $StageRoot
        }
    } else {
        $destinationDir = Split-Path -Parent $destinationPath
        if (-not (Test-Path -LiteralPath $destinationDir)) {
            New-Item -ItemType Directory -Path $destinationDir | Out-Null
        }

        Copy-Item -LiteralPath $SourcePath -Destination $destinationPath -Force
    }
}

if (-not (Test-Path -LiteralPath $bundleDir)) {
    New-Item -ItemType Directory -Path $bundleDir | Out-Null
}

$stageRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("rag-system-release-" + [System.Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $stageRoot | Out-Null

try {
    foreach ($path in $includePaths) {
        $sourcePath = Join-Path $root $path
        if (-not (Test-Path -LiteralPath $sourcePath)) {
            continue
        }

        if (Test-ShouldExclude -RelativePath $path -Name (Split-Path $path -Leaf) -IsDirectory (Test-Path -LiteralPath $sourcePath -PathType Container)) {
            continue
        }

        Copy-IncludedPath -SourcePath $sourcePath -RelativePath $path -StageRoot $stageRoot
    }

    if (Test-Path -LiteralPath $bundlePath) {
        Remove-Item -LiteralPath $bundlePath -Force
    }

    [System.IO.Compression.ZipFile]::CreateFromDirectory($stageRoot, $bundlePath, [System.IO.Compression.CompressionLevel]::Optimal, $false)
} finally {
    if (Test-Path -LiteralPath $stageRoot) {
        Remove-Item -LiteralPath $stageRoot -Recurse -Force
    }
}

Write-Output "Created release ZIP at $bundlePath"
