[CmdletBinding()]
param(
    [string]$BindHost = '127.0.0.1',
    [int]$UserPort = 3000,
    [int]$AdminPort = 3001,
    [int]$BackendPort = 8000,
    [int]$AiPort = 8010,
    [string]$AdminUser = 'localadmin',
    [string]$AdminEmail = 'localadmin@example.com',
    [string]$AdminPassword = 'Admin123456',
    [switch]$ForceDependencyRefresh
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
        Invoke-CommandChecked -Executable $NodeToolchain.NodePath -Arguments @($NodeToolchain.NpmCliPath) + $Arguments -WorkingDirectory $WorkingDirectory
        return
    }

    Invoke-CommandChecked -Executable $NodeToolchain.NpmCommand -Arguments $Arguments -WorkingDirectory $WorkingDirectory
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
    $importProbe = 'import django, rest_framework, corsheaders, channels, celery, pymysql, paramiko, scp, numpy, PIL, reportlab, cv2, sklearn'
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
    param([string]$LocalSettingsPath)

    if (Test-Path -LiteralPath $LocalSettingsPath) {
        return
    }

    Write-Step 'Creating local Django settings'
    $content = @'
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

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://127.0.0.1:8010")
AI_SERVICE_TIMEOUT = int(os.getenv("AI_SERVICE_TIMEOUT", "1200"))
AI_SERVICE_API_TOKEN = os.getenv("AI_SERVICE_API_TOKEN", "")
'@
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

    $needsInstall = $ForceRefresh -or -not (Test-Path -LiteralPath $nodeModulesPath) -or -not (Test-Path -LiteralPath $viteBinary) -or ($lockHash -ne $recordedHash)

    if (-not $needsInstall) {
        return
    }

    Write-Step "Installing $FrontendName frontend dependencies"
    Invoke-NpmCommandChecked -NodeToolchain $NodeToolchain -Arguments @('install', '--no-fund', '--no-audit') -WorkingDirectory $FrontendDir
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
}

function Ensure-LocalAdminUser {
    param(
        [string]$BackendPython,
        [string]$BackendDir,
        [string]$AdminUser,
        [string]$AdminEmail,
        [string]$AdminPassword
    )

    Write-Step 'Ensuring local admin account'
    $bootstrap = @"
from django.contrib.auth import get_user_model

User = get_user_model()
username = '$AdminUser'
email = '$AdminEmail'
password = '$AdminPassword'

user, created = User.objects.get_or_create(
    username=username,
    defaults={
        'email': email,
        'role': 'admin',
        'is_staff': True,
        'is_superuser': True,
    },
)

if created:
    user.set_password(password)
    user.save()
else:
    changed = False
    if user.email != email:
        user.email = email
        changed = True
    if getattr(user, 'role', '') != 'admin':
        user.role = 'admin'
        changed = True
    if not user.is_staff:
        user.is_staff = True
        changed = True
    if not user.is_superuser:
        user.is_superuser = True
        changed = True
    user.set_password(password)
    changed = True
    if changed:
        user.save()

print('ready')
"@
    Invoke-CommandChecked -Executable $BackendPython -Arguments @('manage.py', 'shell', '-c', $bootstrap) -WorkingDirectory $BackendDir
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
        return Start-ManagedProcess -Name $Name -Executable $NodeToolchain.NodePath -Arguments @($NodeToolchain.NpmCliPath) + $NpmArguments -WorkingDirectory $WorkingDirectory -HealthUrl $HealthUrl -LogsDir $LogsDir -Port $Port -TimeoutSeconds $TimeoutSeconds
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
$BackendDir = Find-SingleFileParent -RootDir $RootDir -Filter 'manage.py' -Description 'backend'
$AiDir = Find-SingleFileParent -RootDir $RootDir -Filter 'ai_http_service.py' -Description 'AI service'
$UserFrontendDir = Find-FrontendDirectory -RootDir $RootDir -PackageName 'buaa_se'
$AdminFrontendDir = Find-FrontendDirectory -RootDir $RootDir -PackageName 'BUAA_SE_manage'
$VenvDir = Join-Path $BackendDir '.venv'
$BackendRequirements = Join-Path $BackendDir 'requirements.local.txt'
$LocalSettingsPath = Join-Path $BackendDir 'fake_image_detector\local_settings.py'
$UserEnvPath = Join-Path $UserFrontendDir '.env'
$AdminEnvPath = Join-Path $AdminFrontendDir '.env'
$AiArtifactPath = Join-Path $AiDir 'detection_service\artifacts\minimal_baseline.pkl'

Write-Step 'Preparing local working directories'
Ensure-Directory -Path $LocalDevDir
Ensure-Directory -Path $LogsDir

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

Ensure-LocalSettings -LocalSettingsPath $LocalSettingsPath
Ensure-FrontendEnvFiles -UserEnvPath $UserEnvPath -AdminEnvPath $AdminEnvPath -BindHost $BindHost -BackendPort $BackendPort
Ensure-FrontendDependencies -NodeToolchain $NodeToolchain -FrontendName 'user' -FrontendDir $UserFrontendDir -LocalDevDir $LocalDevDir -ForceRefresh:$ForceDependencyRefresh
Ensure-FrontendDependencies -NodeToolchain $NodeToolchain -FrontendName 'admin' -FrontendDir $AdminFrontendDir -LocalDevDir $LocalDevDir -ForceRefresh:$ForceDependencyRefresh
Ensure-AiModelArtifact -AiArtifactPath $AiArtifactPath -BackendPython $BackendPython -AiDir $AiDir
Ensure-BackendDatabase -BackendPython $BackendPython -BackendDir $BackendDir -BindHost $BindHost -AiPort $AiPort
Ensure-LocalAdminUser -BackendPython $BackendPython -BackendDir $BackendDir -AdminUser $AdminUser -AdminEmail $AdminEmail -AdminPassword $AdminPassword

Write-Step 'Starting local services'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
$env:AI_SERVICE_TIMEOUT_SECONDS = '120'
$aiProcess = Start-ManagedProcess -Name 'ai-service' -Executable $BackendPython -Arguments @('ai_http_service.py', '--host', $BindHost, '--port', "$AiPort") -WorkingDirectory $AiDir -HealthUrl "http://$BindHost`:$AiPort/health" -LogsDir $LogsDir -Port $AiPort -TimeoutSeconds 120

$env:DJANGO_SETTINGS_MODULE = 'fake_image_detector.local_settings'
$env:AI_SERVICE_URL = "http://$BindHost`:$AiPort"
$env:AI_SERVICE_TIMEOUT = '1200'
$backendProcess = Start-ManagedProcess -Name 'django' -Executable $BackendPython -Arguments @('manage.py', 'runserver', "$BindHost`:$BackendPort") -WorkingDirectory $BackendDir -HealthUrl "http://$BindHost`:$BackendPort/admin/" -LogsDir $LogsDir -Port $BackendPort -TimeoutSeconds 120

$userProcess = Start-FrontendDevServer -NodeToolchain $NodeToolchain -FrontendDir $UserFrontendDir -Name 'frontend-user' -BindHost $BindHost -Port $UserPort -LogsDir $LogsDir -HealthUrl "http://$BindHost`:$UserPort/"
$adminProcess = Start-FrontendDevServer -NodeToolchain $NodeToolchain -FrontendDir $AdminFrontendDir -Name 'frontend-admin' -BindHost $BindHost -Port $AdminPort -LogsDir $LogsDir -HealthUrl "http://$BindHost`:$AdminPort/"

$state = @($aiProcess, $backendProcess, $userProcess, $adminProcess)
$state | ConvertTo-Json | Set-Content -LiteralPath $StatePath -Encoding UTF8

Write-Host ''
Write-Host 'Local validation environment is ready:' -ForegroundColor Green
Write-Host "  User frontend:  http://$BindHost`:$UserPort"
Write-Host "  Admin frontend: http://$BindHost`:$AdminPort"
Write-Host "  Django:         http://$BindHost`:$BackendPort/admin/"
Write-Host "  AI service:     http://$BindHost`:$AiPort/health"
Write-Host ''
Write-Host "Node toolchain: $($NodeToolchain.Source) $($NodeToolchain.Version)"
Write-Host "Local admin:    $AdminUser / $AdminPassword"
Write-Host "Logs:           $LogsDir"
Write-Host "Stop with:      .\scripts\stop-local-windows.ps1"
