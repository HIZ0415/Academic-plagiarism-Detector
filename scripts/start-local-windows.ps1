[CmdletBinding()]
param(
    [string]$BindHost = '127.0.0.1',
    [int]$UserPort = 3000,
    [int]$AdminPort = 3001,
    [int]$BackendPort = 8000,
    [int]$AiPort = 8010,
    [string]$LocalOrganizationName = 'Local Demo Organization',
    [string]$LocalOrganizationEmail = 'local-org@example.com',
    [string]$AdminUser = 'admin',
    [string]$AdminEmail = 'admin@mail.com',
    [string]$AdminPassword = 'Admin123!',
    [string]$PublisherUser = 'publisher_test',
    [string]$PublisherEmail = 'publisher_test@example.com',
    [string]$PublisherPassword = 'Publisher123!',
    [string]$ReviewerUser = 'reviewer_test',
    [string]$ReviewerEmail = 'reviewer_test@example.com',
    [string]$ReviewerPassword = 'Reviewer123!',
    [switch]$ForceDependencyRefresh,
    [switch]$FullFrontendMock
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

function Write-Step {
    param([string]$Message)
    Write-Host ''
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Assert-WindowsPlatform {
    if ([System.Environment]::OSVersion.Platform -ne [System.PlatformID]::Win32NT) {
        throw 'This script is Windows-only. Use the Windows startup script on a Windows machine.'
    }
}

function Resolve-RepositoryRoot {
    param([string]$StartDir)

    $current = Resolve-Path -LiteralPath $StartDir
    while ($null -ne $current) {
        $hasGitIgnore = Test-Path -LiteralPath (Join-Path $current.Path '.gitignore')
        $hasReadme = Test-Path -LiteralPath (Join-Path $current.Path 'README.md')
        if ($hasGitIgnore -and $hasReadme) {
            return $current.Path
        }

        $parent = Split-Path -Parent $current.Path
        if (-not $parent -or $parent -eq $current.Path) {
            break
        }

        $current = Resolve-Path -LiteralPath $parent
    }

    throw 'Unable to locate the repository root from the current script directory.'
}

function Ensure-Directory {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

function Find-SingleFileParent {
    param(
        [string]$RootDir,
        [string]$Filter,
        [string]$Description
    )

    $matches = @(Get-ChildItem -LiteralPath $RootDir -Recurse -File -Filter $Filter)
    if ($matches.Count -ne 1) {
        throw "Expected exactly one $Description file named $Filter, found $($matches.Count)."
    }

    return $matches[0].Directory.FullName
}

function Find-FrontendDirectory {
    param(
        [string]$RootDir,
        [string]$PackageName
    )

    $packageFiles = @(Get-ChildItem -LiteralPath $RootDir -Recurse -File -Filter 'package.json')
    foreach ($packageFile in $packageFiles) {
        try {
            $package = Get-Content -LiteralPath $packageFile.FullName -Raw | ConvertFrom-Json
            if ($package.name -eq $PackageName) {
                return $packageFile.Directory.FullName
            }
        }
        catch {
        }
    }

    throw "Unable to locate frontend package $PackageName."
}

function Get-PortProcessIds {
    param([int]$Port)

    $ids = New-Object System.Collections.Generic.List[int]

    if (Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue) {
        try {
            $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop
            foreach ($connection in $connections) {
                if ($connection.OwningProcess -and -not $ids.Contains([int]$connection.OwningProcess)) {
                    $ids.Add([int]$connection.OwningProcess)
                }
            }
        }
        catch {
        }
    }

    if ($ids.Count -eq 0) {
        $matches = netstat -ano -p tcp | Select-String "[:\.]$Port\s"
        foreach ($match in $matches) {
            $text = $match.ToString()
            if ($text -match '\s+(\d+)\s*$') {
                $processId = [int]$Matches[1]
                if ($processId -gt 0 -and -not $ids.Contains($processId)) {
                    $ids.Add($processId)
                }
            }
        }
    }

    return $ids.ToArray()
}

function Stop-ProcessesByPort {
    param(
        [int]$Port,
        [switch]$Quiet
    )

    foreach ($processId in (Get-PortProcessIds -Port $Port)) {
        try {
            Stop-Process -Id $processId -Force -ErrorAction Stop
            if (-not $Quiet) {
                Write-Host "Stopped process $processId on port $Port"
            }
        }
        catch {
            if (-not $Quiet) {
                Write-Warning "Failed to stop process $processId on port ${Port}: $($_.Exception.Message)"
            }
        }
    }
}

function Stop-ManagedProcesses {
    param(
        [string]$StatePath,
        [int[]]$Ports,
        [switch]$Quiet
    )

    if (Test-Path -LiteralPath $StatePath) {
        try {
            $state = Get-Content -LiteralPath $StatePath -Raw | ConvertFrom-Json
        }
        catch {
            $state = @()
        }

        foreach ($entry in @($state)) {
            if ($null -eq $entry -or -not $entry.pid) {
                continue
            }

            try {
                Stop-Process -Id ([int]$entry.pid) -Force -ErrorAction Stop
                if (-not $Quiet) {
                    Write-Host "Stopped $($entry.name) PID $($entry.pid)"
                }
            }
            catch {
            }
        }
    }

    foreach ($port in $Ports) {
        Stop-ProcessesByPort -Port $port -Quiet:$Quiet
    }

    if (Test-Path -LiteralPath $StatePath) {
        Remove-Item -LiteralPath $StatePath -Force
    }
}

function Test-CommandAvailable {
    param([string]$CommandName)
    return $null -ne (Get-Command $CommandName -ErrorAction SilentlyContinue)
}

function ConvertTo-VersionObject {
    param([string]$VersionText)

    $normalized = $VersionText.Trim().TrimStart('v')
    try {
        return [version]$normalized
    }
    catch {
        return $null
    }
}

function Resolve-PythonFromKnownLocations {
    $candidates = @(
        "$env:LocalAppData\Programs\Python\Python312\python.exe",
        "$env:LocalAppData\Programs\Python\Python311\python.exe",
        "$env:ProgramFiles\Python312\python.exe",
        "$env:ProgramFiles\Python311\python.exe",
        'C:\Python312\python.exe',
        'C:\Python311\python.exe'
    )

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    return $null
}

function Resolve-SystemPython {
    $pythonSnippet = 'import json, sys; print(json.dumps({"executable": sys.executable, "version": list(sys.version_info[:3])}))'
    $candidates = @(
        @{ command = 'py'; arguments = @('-3.12', '-c', $pythonSnippet) },
        @{ command = 'py'; arguments = @('-3.11', '-c', $pythonSnippet) },
        @{ command = 'python'; arguments = @('-c', $pythonSnippet) }
    )

    foreach ($candidate in $candidates) {
        if (-not (Test-CommandAvailable -CommandName $candidate.command)) {
            continue
        }

        try {
            $raw = & $candidate.command @($candidate.arguments) 2>$null | Select-Object -First 1
            if (-not $raw) {
                continue
            }

            $result = $raw | ConvertFrom-Json
            $version = [version]::new([int]$result.version[0], [int]$result.version[1], [int]$result.version[2])
            if ($version -ge [version]'3.11.0' -and (Test-Path -LiteralPath $result.executable)) {
                return @{
                    PythonPath = (Resolve-Path -LiteralPath $result.executable).Path
                    Version    = $version
                }
            }
        }
        catch {
        }
    }

    $knownPython = Resolve-PythonFromKnownLocations
    if ($knownPython) {
        try {
            $raw = & $knownPython -c $pythonSnippet 2>$null | Select-Object -First 1
            $result = $raw | ConvertFrom-Json
            $version = [version]::new([int]$result.version[0], [int]$result.version[1], [int]$result.version[2])
            if ($version -ge [version]'3.11.0') {
                return @{
                    PythonPath = (Resolve-Path -LiteralPath $result.executable).Path
                    Version    = $version
                }
            }
        }
        catch {
        }
    }

    return $null
}

function Install-PythonOnWindows {
    if (Test-CommandAvailable -CommandName 'winget') {
        Write-Step 'Python not found. Installing Python 3.12 with winget.'
        & winget install --id Python.Python.3.12 -e --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -eq 0) {
            return
        }
    }

    if (Test-CommandAvailable -CommandName 'choco') {
        Write-Step 'Python not found. Installing Python 3.12 with Chocolatey.'
        & choco install python312 -y
        if ($LASTEXITCODE -eq 0) {
            return
        }
    }

    throw 'Python 3.11+ is missing and automatic installation failed. Install Python manually, then rerun the script.'
}

function Ensure-BootstrapPython {
    $python = Resolve-SystemPython
    if ($python) {
        return $python
    }

    Install-PythonOnWindows

    $python = Resolve-SystemPython
    if (-not $python) {
        throw 'Python installation completed, but python.exe is still unavailable in this shell. Reopen PowerShell and rerun the script.'
    }

    return $python
}

function Resolve-SystemNodeToolchain {
    $nodeCommand = Get-Command node -ErrorAction SilentlyContinue
    $npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if ($null -eq $nodeCommand -or $null -eq $npmCommand) {
        return $null
    }

    try {
        $versionText = (& $nodeCommand.Source -p "process.versions.node" 2>$null | Select-Object -First 1).Trim()
        $version = ConvertTo-VersionObject -VersionText $versionText
        if ($null -eq $version -or $version -lt [version]'20.0.0') {
            return $null
        }

        return @{
            Source        = 'system'
            NodePath      = $nodeCommand.Source
            NpmCommand    = $npmCommand.Source
            NpmCliPath    = $null
            Version       = $version
        }
    }
    catch {
        return $null
    }
}

function Resolve-PortableNodeToolchain {
    param([string]$NodeDir)

    $nodePath = Join-Path $NodeDir 'node.exe'
    $npmCliPath = Join-Path $NodeDir 'node_modules\npm\bin\npm-cli.js'
    if (-not (Test-Path -LiteralPath $nodePath) -or -not (Test-Path -LiteralPath $npmCliPath)) {
        return $null
    }

    try {
        $versionText = (& $nodePath -p "process.versions.node" 2>$null | Select-Object -First 1).Trim()
        $version = ConvertTo-VersionObject -VersionText $versionText
        if ($null -eq $version -or $version -lt [version]'20.0.0') {
            return $null
        }

        return @{
            Source        = 'portable'
            NodePath      = $nodePath
            NpmCommand    = $null
            NpmCliPath    = $npmCliPath
            Version       = $version
        }
    }
    catch {
        return $null
    }
}

function Resolve-NodeFromKnownLocations {
    $nodePath = Join-Path $env:ProgramFiles 'nodejs\node.exe'
    $npmPath = Join-Path $env:ProgramFiles 'nodejs\npm.cmd'
    if ((Test-Path -LiteralPath $nodePath) -and (Test-Path -LiteralPath $npmPath)) {
        try {
            $versionText = (& $nodePath -p "process.versions.node" 2>$null | Select-Object -First 1).Trim()
            $version = ConvertTo-VersionObject -VersionText $versionText
            if ($null -ne $version -and $version -ge [version]'20.0.0') {
                return @{
                    Source     = 'system'
                    NodePath   = $nodePath
                    NpmCommand = $npmPath
                    NpmCliPath = $null
                    Version    = $version
                }
            }
        }
        catch {
        }
    }

    return $null
}

function Install-PortableNodeRuntime {
    param(
        [string]$RootDir,
        [string]$LocalDevDir,
        [string]$Version
    )

    $nodeDir = Join-Path $RootDir '.tools\node'
    $downloadDir = Join-Path $LocalDevDir 'downloads'
    $zipPath = Join-Path $downloadDir "node-v$Version-win-x64.zip"
    $extractRoot = Join-Path $downloadDir "node-v$Version-win-x64"
    $downloadUrl = "https://nodejs.org/dist/v$Version/node-v$Version-win-x64.zip"

    Ensure-Directory -Path $downloadDir

    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

    Write-Step "Installing portable Node.js runtime v$Version"

    if (-not (Test-Path -LiteralPath $zipPath)) {
        Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath
    }

    if (Test-Path -LiteralPath $extractRoot) {
        Remove-Item -LiteralPath $extractRoot -Recurse -Force
    }

    Expand-Archive -LiteralPath $zipPath -DestinationPath $downloadDir -Force

    if (Test-Path -LiteralPath $nodeDir) {
        Remove-Item -LiteralPath $nodeDir -Recurse -Force
    }

    Ensure-Directory -Path $nodeDir
    Get-ChildItem -LiteralPath $extractRoot -Force | ForEach-Object {
        Move-Item -LiteralPath $_.FullName -Destination $nodeDir
    }

    return $nodeDir
}

function Install-SystemNodeRuntime {
    if (Test-CommandAvailable -CommandName 'winget') {
        Write-Step 'Node.js not found. Installing Node.js LTS with winget.'
        & winget install --id OpenJS.NodeJS.LTS -e --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -eq 0) {
            return
        }
    }

    if (Test-CommandAvailable -CommandName 'choco') {
        Write-Step 'Node.js not found. Installing Node.js LTS with Chocolatey.'
        & choco install nodejs-lts -y
        if ($LASTEXITCODE -eq 0) {
            return
        }
    }

    throw 'Node.js 20+ is missing and automatic installation failed. Install Node.js manually, then rerun the script.'
}

function Ensure-NodeToolchain {
    param(
        [string]$RootDir,
        [string]$LocalDevDir,
        [string]$Version
    )

    $systemToolchain = Resolve-SystemNodeToolchain
    if ($systemToolchain) {
        return $systemToolchain
    }

    $portableToolchain = Resolve-PortableNodeToolchain -NodeDir (Join-Path $RootDir '.tools\node')
    if ($portableToolchain) {
        return $portableToolchain
    }

    try {
        $nodeDir = Install-PortableNodeRuntime -RootDir $RootDir -LocalDevDir $LocalDevDir -Version $Version
        $portableToolchain = Resolve-PortableNodeToolchain -NodeDir $nodeDir
        if ($portableToolchain) {
            return $portableToolchain
        }
    }
    catch {
        Write-Warning "Portable Node.js installation failed: $($_.Exception.Message)"
    }

    Install-SystemNodeRuntime

    $systemToolchain = Resolve-SystemNodeToolchain
    if ($systemToolchain) {
        return $systemToolchain
    }

    $systemToolchain = Resolve-NodeFromKnownLocations
    if ($systemToolchain) {
        return $systemToolchain
    }

    throw 'Node.js installation completed, but node.exe/npm.cmd are still unavailable in this shell.'
}

function Invoke-CommandChecked {
    param(
        [string]$Executable,
        [string[]]$Arguments,
        [string]$WorkingDirectory
    )

    Push-Location -LiteralPath $WorkingDirectory
    try {
        & $Executable @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed: $Executable $($Arguments -join ' ')"
        }
    }
    finally {
        Pop-Location
    }
}

function Invoke-NpmCommandChecked {
    param(
        [hashtable]$NodeToolchain,
        [string[]]$Arguments,
        [string]$WorkingDirectory
    )

    if ($NodeToolchain.NpmCliPath) {
        $nodeArguments = @($NodeToolchain.NpmCliPath) + $Arguments
        Invoke-CommandChecked -Executable $NodeToolchain.NodePath -Arguments $nodeArguments -WorkingDirectory $WorkingDirectory
        return
    }

    Invoke-CommandChecked -Executable $NodeToolchain.NpmCommand -Arguments $Arguments -WorkingDirectory $WorkingDirectory
}

function Invoke-NpmInstallWithRetry {
    param(
        [hashtable]$NodeToolchain,
        [string]$WorkingDirectory
    )

    $installArgs = @('install', '--no-fund', '--no-audit')
    if (-not [string]::IsNullOrWhiteSpace($env:LOCAL_NPM_REGISTRY)) {
        $installArgs += @(
            "--registry=$env:LOCAL_NPM_REGISTRY",
            '--replace-registry-host=always'
        )
    }
    $originalRegistry = $env:npm_config_registry
    try {
        Invoke-NpmCommandChecked -NodeToolchain $NodeToolchain -Arguments $installArgs -WorkingDirectory $WorkingDirectory
        return
    }
    catch {
        Write-Warning "npm install failed: $($_.Exception.Message)"
    }

    $retryRegistry = if ([string]::IsNullOrWhiteSpace($env:LOCAL_NPM_REGISTRY)) { 'https://registry.npmjs.org/' } else { $env:LOCAL_NPM_REGISTRY }
    Write-Warning "Retrying npm install with cache preference disabled and registry $retryRegistry."
    try {
        $env:npm_config_registry = $retryRegistry
        Invoke-NpmCommandChecked -NodeToolchain $NodeToolchain -Arguments @(
            'install',
            '--no-fund',
            '--no-audit',
            '--prefer-online',
            '--replace-registry-host=always',
            "--registry=$retryRegistry"
        ) -WorkingDirectory $WorkingDirectory
    }
    finally {
        if ($null -eq $originalRegistry) {
            Remove-Item Env:\npm_config_registry -ErrorAction SilentlyContinue
        }
        else {
            $env:npm_config_registry = $originalRegistry
        }
    }
}

function Ensure-BackendVenv {
    param(
        [string]$BootstrapPythonPath,
        [string]$VenvDir,
        [string]$BackendDir
    )

    $venvPython = Join-Path $VenvDir 'Scripts\python.exe'
    if (Test-Path -LiteralPath $venvPython) {
        return $venvPython
    }

    Write-Step 'Creating backend virtual environment'
    Invoke-CommandChecked -Executable $BootstrapPythonPath -Arguments @('-m', 'venv', $VenvDir) -WorkingDirectory $BackendDir
    return $venvPython
}

function Ensure-BackendDependencies {
    param(
        [string]$BackendPython,
        [string]$BackendDir,
        [string]$BackendRequirements,
        [string]$LocalDevDir,
        [switch]$ForceRefresh
    )

    Ensure-Directory -Path $LocalDevDir
    $stampPath = Join-Path $LocalDevDir 'backend-requirements.sha256'
    $requirementsHash = (Get-FileHash -LiteralPath $BackendRequirements -Algorithm SHA256).Hash
    $recordedHash = if (Test-Path -LiteralPath $stampPath) { (Get-Content -LiteralPath $stampPath -Raw).Trim() } else { '' }
    $importProbe = 'import django, rest_framework, corsheaders, channels, celery, pymysql, paramiko, scp, numpy, PIL, fitz, reportlab, cv2, sklearn'
    $importsHealthy = $false

    try {
        Invoke-CommandChecked -Executable $BackendPython -Arguments @('-c', $importProbe) -WorkingDirectory $BackendDir
        $importsHealthy = $true
    }
    catch {
    }

    if ($importsHealthy -and -not $ForceRefresh -and $requirementsHash -eq $recordedHash) {
        return
    }

    if ($importsHealthy -and -not $ForceRefresh -and $requirementsHash -ne $recordedHash) {
        Set-Content -LiteralPath $stampPath -Value $requirementsHash -Encoding UTF8
        return
    }

    Write-Step 'Installing or updating backend dependencies'
    Invoke-CommandChecked -Executable $BackendPython -Arguments @('-m', 'pip', 'install', '--disable-pip-version-check', '--upgrade', 'pip', 'setuptools', 'wheel') -WorkingDirectory $BackendDir
    Invoke-CommandChecked -Executable $BackendPython -Arguments @('-m', 'pip', 'install', '--disable-pip-version-check', '-r', $BackendRequirements) -WorkingDirectory $BackendDir
    Set-Content -LiteralPath $stampPath -Value $requirementsHash -Encoding UTF8
}

function Ensure-LocalSettings {
    param(
        [string]$LocalSettingsPath,
        [string]$BindHost,
        [int]$AiPort
    )

    if (Test-Path -LiteralPath $LocalSettingsPath) {
        return
    }

    Write-Step 'Creating local Django settings'
    $aiServiceUrl = "http://$BindHost`:$AiPort"
    $content = @"
import os

from .settings import *

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "$aiServiceUrl")
AI_SERVICE_TIMEOUT = int(os.getenv("AI_SERVICE_TIMEOUT", "1200"))
AI_SERVICE_API_TOKEN = os.getenv("AI_SERVICE_API_TOKEN", "")
"@
    Set-Content -LiteralPath $LocalSettingsPath -Value $content -Encoding UTF8
}

function Set-DotEnvValue {
    param(
        [string]$Path,
        [string]$Key,
        [string]$Value
    )

    $line = "$Key=$Value"
    if (-not (Test-Path -LiteralPath $Path)) {
        Set-Content -LiteralPath $Path -Value $line -Encoding UTF8
        return
    }

    $lines = [System.Collections.Generic.List[string]]::new()
    $found = $false
    foreach ($existingLine in Get-Content -LiteralPath $Path) {
        if ($existingLine.StartsWith("$Key=")) {
            $lines.Add($line)
            $found = $true
        }
        else {
            $lines.Add($existingLine)
        }
    }

    if (-not $found) {
        $lines.Add($line)
    }

    Set-Content -LiteralPath $Path -Value $lines -Encoding UTF8
}

function Ensure-FrontendEnvFiles {
    param(
        [string]$UserEnvPath,
        [string]$AdminEnvPath,
        [string]$BindHost,
        [int]$BackendPort
    )

    Write-Step 'Syncing frontend local environment files'
    $apiUrl = "http://$BindHost`:$BackendPort"
    Set-DotEnvValue -Path $UserEnvPath -Key 'VITE_API_URL' -Value $apiUrl
    Set-DotEnvValue -Path $AdminEnvPath -Key 'VITE_API_URL' -Value $apiUrl
}

function Ensure-FrontendDependencies {
    param(
        [hashtable]$NodeToolchain,
        [string]$FrontendName,
        [string]$FrontendDir,
        [string]$LocalDevDir,
        [switch]$ForceRefresh
    )

    $lockPath = Join-Path $FrontendDir 'package-lock.json'
    $nodeModulesPath = Join-Path $FrontendDir 'node_modules'
    $stampPath = Join-Path $LocalDevDir "$FrontendName-package-lock.sha256"
    $lockHash = (Get-FileHash -LiteralPath $lockPath -Algorithm SHA256).Hash
    $recordedHash = if (Test-Path -LiteralPath $stampPath) { (Get-Content -LiteralPath $stampPath -Raw).Trim() } else { '' }
    $viteBinary = Join-Path $FrontendDir 'node_modules\.bin\vite.cmd'
    $viteCliPath = Join-Path $FrontendDir 'node_modules\vite\bin\vite.js'

    if (-not $ForceRefresh -and (Test-Path -LiteralPath $nodeModulesPath) -and (Test-Path -LiteralPath $viteBinary) -and (Test-Path -LiteralPath $viteCliPath)) {
        if ($lockHash -ne $recordedHash) {
            Set-Content -LiteralPath $stampPath -Value $lockHash -Encoding UTF8
        }
        return
    }

    $needsInstall = $ForceRefresh -or -not (Test-Path -LiteralPath $nodeModulesPath) -or -not (Test-Path -LiteralPath $viteBinary) -or -not (Test-Path -LiteralPath $viteCliPath) -or ($lockHash -ne $recordedHash)

    if (-not $needsInstall) {
        return
    }

    Write-Step "Installing $FrontendName frontend dependencies"
    if ($ForceRefresh -and (Test-Path -LiteralPath $nodeModulesPath)) {
        try {
            Remove-Item -LiteralPath $nodeModulesPath -Recurse -Force -ErrorAction Stop
        }
        catch {
            Write-Warning "Unable to remove existing node_modules for ${FrontendName}: $($_.Exception.Message)"
            Write-Warning 'Continuing with npm install; npm will repair or replace packages where possible.'
        }
    }
    Invoke-NpmInstallWithRetry -NodeToolchain $NodeToolchain -WorkingDirectory $FrontendDir
    if (-not (Test-Path -LiteralPath $viteBinary) -or -not (Test-Path -LiteralPath $viteCliPath)) {
        throw "Frontend dependency install for $FrontendName finished, but Vite is still missing. Run this script again with -ForceDependencyRefresh after checking npm access."
    }
    Set-Content -LiteralPath $stampPath -Value $lockHash -Encoding UTF8
}

function Ensure-AiModelArtifact {
    param(
        [string]$AiArtifactPath,
        [string]$BackendPython,
        [string]$AiDir
    )

    if (Test-Path -LiteralPath $AiArtifactPath) {
        return
    }

    Write-Step 'Minimal AI model artifact is missing. Training local baseline model.'
    Invoke-CommandChecked -Executable $BackendPython -Arguments @('train_minimal_baseline.py') -WorkingDirectory $AiDir
}

function Ensure-BackendDatabase {
    param(
        [string]$BackendPython,
        [string]$BackendDir,
        [string]$BindHost,
        [int]$AiPort
    )

    Write-Step 'Running Django database initialization'
    $env:DJANGO_SETTINGS_MODULE = 'fake_image_detector.local_settings'
    $env:AI_SERVICE_URL = "http://$BindHost`:$AiPort"
    $env:AI_SERVICE_TIMEOUT = '1200'
    $env:AI_SERVICE_TIMEOUT_SECONDS = '120'
    Invoke-CommandChecked -Executable $BackendPython -Arguments @('manage.py', 'migrate', '--run-syncdb', '--noinput') -WorkingDirectory $BackendDir
    Invoke-CommandChecked -Executable $BackendPython -Arguments @('manage.py', 'migrate_detection_task_v2') -WorkingDirectory $BackendDir
    Invoke-CommandChecked -Executable $BackendPython -Arguments @('manage.py', 'backfill_detection_task_v2') -WorkingDirectory $BackendDir
}

function ConvertTo-PythonJsonLiteral {
    param([hashtable]$Value)

    return ($Value | ConvertTo-Json -Compress)
}

function Ensure-LocalDemoAccounts {
    param(
        [string]$BackendPython,
        [string]$BackendDir,
        [string]$OrganizationName,
        [string]$OrganizationEmail,
        [string]$AdminUser,
        [string]$AdminEmail,
        [string]$AdminPassword,
        [string]$PublisherUser,
        [string]$PublisherEmail,
        [string]$PublisherPassword,
        [string]$ReviewerUser,
        [string]$ReviewerEmail,
        [string]$ReviewerPassword
    )

    Write-Step 'Ensuring local demo accounts'
    $payload = ConvertTo-PythonJsonLiteral -Value @{
        organization_name  = $OrganizationName
        organization_email = $OrganizationEmail
        admin_user         = $AdminUser
        admin_email        = $AdminEmail
        admin_password     = $AdminPassword
        publisher_user     = $PublisherUser
        publisher_email    = $PublisherEmail
        publisher_password = $PublisherPassword
        reviewer_user      = $ReviewerUser
        reviewer_email     = $ReviewerEmail
        reviewer_password  = $ReviewerPassword
    }
    $bootstrap = @"
import json
import os
import sys

sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fake_image_detector.local_settings')

import django
django.setup()

from django.contrib.auth import get_user_model
from core.models import Organization, PublisherReviewerRelationship

cfg = json.loads(r'''$payload''')
User = get_user_model()

org = (
    Organization.objects.filter(email=cfg['organization_email']).first()
    or Organization.objects.filter(name=cfg['organization_name']).first()
    or Organization()
)
org.name = cfg['organization_name']
org.email = cfg['organization_email']
org.save()

def ensure_user(username, email, password, role, *, staff=False, superuser=False):
    user = User.objects.filter(username=username).first()
    if user is None:
        user = User(username=username)
    user.email = email
    user.role = role
    user.organization = org
    user.is_staff = staff
    user.is_superuser = superuser
    user.set_password(password)
    user.save()
    return user

admin = ensure_user(
    cfg['admin_user'],
    cfg['admin_email'],
    cfg['admin_password'],
    'admin',
    staff=True,
    superuser=True,
)
publisher = ensure_user(
    cfg['publisher_user'],
    cfg['publisher_email'],
    cfg['publisher_password'],
    'publisher',
)
reviewer = ensure_user(
    cfg['reviewer_user'],
    cfg['reviewer_email'],
    cfg['reviewer_password'],
    'reviewer',
)

if org.admin_user_id != admin.id:
    org.admin_user = admin
    org.save(update_fields=['admin_user'])

PublisherReviewerRelationship.objects.update_or_create(
    publisher=publisher,
    reviewer=reviewer,
    defaults={'is_active': True},
)

print('ready')
"@
    $bootstrapPath = Join-Path ([System.IO.Path]::GetTempPath()) 'academic_plagiarism_detector_demo_accounts.py'

    try {
        Set-Content -LiteralPath $bootstrapPath -Value $bootstrap -Encoding UTF8
        Invoke-CommandChecked -Executable $BackendPython -Arguments @($bootstrapPath) -WorkingDirectory $BackendDir
    }
    finally {
        Remove-Item -LiteralPath $bootstrapPath -Force -ErrorAction SilentlyContinue
    }
}

function Wait-HttpReady {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 90,
        [int]$ProcessId = 0
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if ($ProcessId -gt 0 -and -not (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)) {
            return $false
        }

        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return $true
            }
        }
        catch {
        }

        Start-Sleep -Seconds 2
    }

    return $false
}

function Get-LogTail {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return ''
    }

    return (Get-Content -LiteralPath $Path -Tail 40 | Out-String).Trim()
}

function Start-ManagedProcess {
    param(
        [string]$Name,
        [string]$Executable,
        [string[]]$Arguments,
        [string]$WorkingDirectory,
        [string]$HealthUrl,
        [string]$LogsDir,
        [int]$Port,
        [int]$TimeoutSeconds = 90
    )

    Ensure-Directory -Path $LogsDir
    $stdoutPath = Join-Path $LogsDir "$Name.stdout.log"
    $stderrPath = Join-Path $LogsDir "$Name.stderr.log"

    foreach ($logPath in @($stdoutPath, $stderrPath)) {
        if (Test-Path -LiteralPath $logPath) {
            Remove-Item -LiteralPath $logPath -Force
        }
    }

    $process = Start-Process -FilePath $Executable -ArgumentList $Arguments -WorkingDirectory $WorkingDirectory -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath -PassThru -WindowStyle Hidden
    if (-not $process) {
        throw "Unable to start $Name."
    }

    if (-not (Wait-HttpReady -Url $HealthUrl -TimeoutSeconds $TimeoutSeconds -ProcessId $process.Id)) {
        try {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        }
        catch {
        }

        $stderrTail = Get-LogTail -Path $stderrPath
        $stdoutTail = Get-LogTail -Path $stdoutPath
        throw "$Name failed to start.`nSTDERR:`n$stderrTail`nSTDOUT:`n$stdoutTail"
    }

    return [pscustomobject]@{
        name      = $Name
        pid       = $process.Id
        port      = $Port
        healthUrl = $HealthUrl
        stdout    = $stdoutPath
        stderr    = $stderrPath
    }
}

function Start-NpmManagedProcess {
    param(
        [hashtable]$NodeToolchain,
        [string]$Name,
        [string[]]$NpmArguments,
        [string]$WorkingDirectory,
        [string]$HealthUrl,
        [string]$LogsDir,
        [int]$Port,
        [int]$TimeoutSeconds = 90
    )

    if ($NodeToolchain.NpmCliPath) {
        $nodeArguments = @($NodeToolchain.NpmCliPath) + $NpmArguments
        return Start-ManagedProcess -Name $Name -Executable $NodeToolchain.NodePath -Arguments $nodeArguments -WorkingDirectory $WorkingDirectory -HealthUrl $HealthUrl -LogsDir $LogsDir -Port $Port -TimeoutSeconds $TimeoutSeconds
    }

    return Start-ManagedProcess -Name $Name -Executable $NodeToolchain.NpmCommand -Arguments $NpmArguments -WorkingDirectory $WorkingDirectory -HealthUrl $HealthUrl -LogsDir $LogsDir -Port $Port -TimeoutSeconds $TimeoutSeconds
}

function Start-FrontendDevServer {
    param(
        [hashtable]$NodeToolchain,
        [string]$FrontendDir,
        [string]$Name,
        [string]$BindHost,
        [int]$Port,
        [string]$LogsDir,
        [string]$HealthUrl
    )

    $viteCliPath = Join-Path $FrontendDir 'node_modules\vite\bin\vite.js'
    if (-not (Test-Path -LiteralPath $viteCliPath)) {
        throw "Vite CLI was not found for $Name at $viteCliPath"
    }

    return Start-ManagedProcess -Name $Name -Executable $NodeToolchain.NodePath -Arguments @($viteCliPath, '--host', $BindHost, '--port', "$Port", '--strictPort') -WorkingDirectory $FrontendDir -HealthUrl $HealthUrl -LogsDir $LogsDir -Port $Port -TimeoutSeconds 120
}

Assert-WindowsPlatform

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Resolve-RepositoryRoot -StartDir $ScriptDir
$LocalDevDir = Join-Path $RootDir '.local-dev'
$LogsDir = Join-Path $LocalDevDir 'logs'
$StatePath = Join-Path $LocalDevDir 'processes.json'
$PortableNodeVersion = if ($env:LOCAL_NODE_VERSION) { $env:LOCAL_NODE_VERSION } else { '22.15.0' }
$Ports = @($UserPort, $AdminPort, $BackendPort, $AiPort)

Write-Step 'Resolving project directories'
# 优先使用本仓库约定路径，避免对整个目录树递归（会扫过 node_modules，极慢或看似卡死）
$BackendDirGuess = Join-Path $RootDir '代码\后端\后端代码'
$AiDirGuess = Join-Path $RootDir '代码\AI服务\AI服务器代码'
$UserFrontendDirGuess = Join-Path $RootDir '代码\前端\前端用户端'
$AdminFrontendDirGuess = Join-Path $RootDir '代码\前端\前端管理端'

if (Test-Path -LiteralPath (Join-Path $BackendDirGuess 'manage.py')) {
    $BackendDir = $BackendDirGuess
}
else {
    $BackendDir = Find-SingleFileParent -RootDir $RootDir -Filter 'manage.py' -Description 'backend'
}

if (Test-Path -LiteralPath (Join-Path $AiDirGuess 'ai_http_service.py')) {
    $AiDir = $AiDirGuess
}
else {
    $AiDir = Find-SingleFileParent -RootDir $RootDir -Filter 'ai_http_service.py' -Description 'AI service'
}

function Resolve-FrontendDirByPackageName {
    param(
        [string]$RootDir,
        [string]$GuessDir,
        [string]$PackageName
    )

    $pkgPath = Join-Path $GuessDir 'package.json'
    if (Test-Path -LiteralPath $pkgPath) {
        try {
            $pkg = Get-Content -LiteralPath $pkgPath -Raw | ConvertFrom-Json
            if ($pkg.name -eq $PackageName) {
                return $GuessDir
            }
        }
        catch {
        }
    }

    return (Find-FrontendDirectory -RootDir $RootDir -PackageName $PackageName)
}

$UserFrontendDir = Resolve-FrontendDirByPackageName -RootDir $RootDir -GuessDir $UserFrontendDirGuess -PackageName 'buaa_se'
$AdminFrontendDir = Resolve-FrontendDirByPackageName -RootDir $RootDir -GuessDir $AdminFrontendDirGuess -PackageName 'BUAA_SE_manage'
$VenvDir = Join-Path $BackendDir '.venv'
$BackendRequirements = Join-Path $BackendDir 'requirements.local.txt'
$LocalSettingsPath = Join-Path $BackendDir 'fake_image_detector\local_settings.py'
$UserEnvPath = Join-Path $UserFrontendDir '.env'
$AdminEnvPath = Join-Path $AdminFrontendDir '.env'
$AiArtifactPath = Join-Path $AiDir 'detection_service\artifacts\minimal_baseline.pkl'

Write-Step 'Preparing local working directories'
Ensure-Directory -Path $LocalDevDir
Ensure-Directory -Path $LogsDir
Ensure-Directory -Path (Join-Path $LocalDevDir 'npm-cache')
Ensure-Directory -Path (Join-Path $LocalDevDir 'tmp')
$env:npm_config_cache = Join-Path $LocalDevDir 'npm-cache'
$env:npm_config_update_notifier = 'false'
$env:TEMP = Join-Path $LocalDevDir 'tmp'
$env:TMP = Join-Path $LocalDevDir 'tmp'

Write-Step 'Stopping existing local service processes'
Stop-ManagedProcesses -StatePath $StatePath -Ports $Ports -Quiet

Write-Step 'Checking Python environment'
$ExistingVenvPython = Join-Path $VenvDir 'Scripts\python.exe'
if (Test-Path -LiteralPath $ExistingVenvPython) {
    $BackendPython = $ExistingVenvPython
}
else {
    $pythonInfo = Ensure-BootstrapPython
    $BackendPython = Ensure-BackendVenv -BootstrapPythonPath $pythonInfo.PythonPath -VenvDir $VenvDir -BackendDir $BackendDir
}
Ensure-BackendDependencies -BackendPython $BackendPython -BackendDir $BackendDir -BackendRequirements $BackendRequirements -LocalDevDir $LocalDevDir -ForceRefresh:$ForceDependencyRefresh

Write-Step 'Checking Node.js environment'
$NodeToolchain = Ensure-NodeToolchain -RootDir $RootDir -LocalDevDir $LocalDevDir -Version $PortableNodeVersion
$nodeBinDir = Split-Path -Parent $NodeToolchain.NodePath
if ($env:Path -notlike "*$nodeBinDir*") {
    $env:Path = "$nodeBinDir;$env:Path"
}

Ensure-LocalSettings -LocalSettingsPath $LocalSettingsPath -BindHost $BindHost -AiPort $AiPort
Ensure-FrontendEnvFiles -UserEnvPath $UserEnvPath -AdminEnvPath $AdminEnvPath -BindHost $BindHost -BackendPort $BackendPort
if ($FullFrontendMock) {
    Write-Step 'User frontend: enabling VITE_USE_FULL_FRONTEND_MOCK'
    Set-DotEnvValue -Path $UserEnvPath -Key 'VITE_USE_FULL_FRONTEND_MOCK' -Value 'true'
    Set-DotEnvValue -Path $UserEnvPath -Key 'VITE_API_URL' -Value ''
}
else {
    Write-Step 'User frontend: real backend mode (disabling full-stack / workflow mock flags)'
    Set-DotEnvValue -Path $UserEnvPath -Key 'VITE_USE_FULL_FRONTEND_MOCK' -Value 'false'
    Set-DotEnvValue -Path $UserEnvPath -Key 'VITE_USE_MOCK_MANUAL_REVIEW_WORKFLOW' -Value 'false'
}
Ensure-FrontendDependencies -NodeToolchain $NodeToolchain -FrontendName 'user' -FrontendDir $UserFrontendDir -LocalDevDir $LocalDevDir -ForceRefresh:$ForceDependencyRefresh
Ensure-FrontendDependencies -NodeToolchain $NodeToolchain -FrontendName 'admin' -FrontendDir $AdminFrontendDir -LocalDevDir $LocalDevDir -ForceRefresh:$ForceDependencyRefresh
Ensure-AiModelArtifact -AiArtifactPath $AiArtifactPath -BackendPython $BackendPython -AiDir $AiDir
Ensure-BackendDatabase -BackendPython $BackendPython -BackendDir $BackendDir -BindHost $BindHost -AiPort $AiPort
Ensure-LocalDemoAccounts `
    -BackendPython $BackendPython `
    -BackendDir $BackendDir `
    -OrganizationName $LocalOrganizationName `
    -OrganizationEmail $LocalOrganizationEmail `
    -AdminUser $AdminUser `
    -AdminEmail $AdminEmail `
    -AdminPassword $AdminPassword `
    -PublisherUser $PublisherUser `
    -PublisherEmail $PublisherEmail `
    -PublisherPassword $PublisherPassword `
    -ReviewerUser $ReviewerUser `
    -ReviewerEmail $ReviewerEmail `
    -ReviewerPassword $ReviewerPassword

Write-Step 'Starting local services'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
$env:AI_SERVICE_TIMEOUT_SECONDS = '120'
# URL 一律用 ASCII 拼接，兼容 Windows PowerShell 5.1 与各类文件编码
$aiHealthUrl = 'http://' + $BindHost + ':' + $AiPort + '/health'
$aiProcess = Start-ManagedProcess -Name 'ai-service' -Executable $BackendPython -Arguments @('ai_http_service.py', '--host', $BindHost, '--port', "$AiPort") -WorkingDirectory $AiDir -HealthUrl $aiHealthUrl -LogsDir $LogsDir -Port $AiPort -TimeoutSeconds 120

$env:DJANGO_SETTINGS_MODULE = 'fake_image_detector.local_settings'
$env:AI_SERVICE_URL = 'http://' + $BindHost + ':' + $AiPort
$env:AI_SERVICE_TIMEOUT = '1200'
$djangoHealthUrl = 'http://' + $BindHost + ':' + $BackendPort + '/admin/'
$djangoListen = $BindHost + ':' + $BackendPort
$backendProcess = Start-ManagedProcess -Name 'django' -Executable $BackendPython -Arguments @('manage.py', 'runserver', $djangoListen) -WorkingDirectory $BackendDir -HealthUrl $djangoHealthUrl -LogsDir $LogsDir -Port $BackendPort -TimeoutSeconds 120

$userHealthUrl = 'http://' + $BindHost + ':' + $UserPort + '/'
$adminHealthUrl = 'http://' + $BindHost + ':' + $AdminPort + '/'
$userProcess = Start-FrontendDevServer -NodeToolchain $NodeToolchain -FrontendDir $UserFrontendDir -Name 'frontend-user' -BindHost $BindHost -Port $UserPort -LogsDir $LogsDir -HealthUrl $userHealthUrl
$adminProcess = Start-FrontendDevServer -NodeToolchain $NodeToolchain -FrontendDir $AdminFrontendDir -Name 'frontend-admin' -BindHost $BindHost -Port $AdminPort -LogsDir $LogsDir -HealthUrl $adminHealthUrl

$state = @($aiProcess, $backendProcess, $userProcess, $adminProcess)
$state | ConvertTo-Json | Set-Content -LiteralPath $StatePath -Encoding UTF8

Write-Host ''
Write-Host 'Local validation environment is ready:' -ForegroundColor Green
# 仅用 ASCII 拼接，避免 PS 5.1 对 -f / 花括号与「智能引号」文件的解析问题
Write-Host ('  User frontend:  http://' + $BindHost + ':' + $UserPort)
Write-Host ('  Admin frontend: http://' + $BindHost + ':' + $AdminPort)
Write-Host ('  Django:         http://' + $BindHost + ':' + $BackendPort + '/admin/')
Write-Host ('  AI service:     http://' + $BindHost + ':' + $AiPort + '/health')
Write-Host ''
Write-Host ('Node toolchain: ' + $NodeToolchain.Source + ' ' + $NodeToolchain.Version)
Write-Host ('Admin login:    ' + $AdminEmail + ' / ' + $AdminPassword)
Write-Host ('Publisher:      ' + $PublisherEmail + ' / ' + $PublisherPassword)
Write-Host ('Reviewer:       ' + $ReviewerEmail + ' / ' + $ReviewerPassword)
Write-Host ('Logs:           ' + $LogsDir)
Write-Host 'Stop with:      .\scripts\stop-local-windows.ps1'
if ($FullFrontendMock) {
    Write-Host ''
    Write-Host 'User client is in full frontend mock mode. Login without Django. Notifications use HTTP polling.' -ForegroundColor Yellow
}
