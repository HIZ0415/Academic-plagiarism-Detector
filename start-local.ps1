[CmdletBinding()]
param(
    [string]$BindHost = '127.0.0.1',
    [int]$UserPort = 3000,
    [int]$AdminPort = 3001,
    [int]$BackendPort = 8000,
    [int]$AiPort = 8010,
    [string]$AdminUser = 'localadmin',
    [string]$AdminEmail = 'localadmin@example.com',
    [string]$AdminPassword = 'Admin123456'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LocalDevDir = Join-Path $RootDir '.local-dev'
$LogsDir = Join-Path $LocalDevDir 'logs'
$StatePath = Join-Path $LocalDevDir 'processes.json'
$BackendDir = $null
$AiDir = $null
$UserFrontendDir = $null
$AdminFrontendDir = $null
$VenvDir = $null
$BackendPython = $null
$BackendRequirements = $null
$LocalSettingsPath = $null
$UserEnvPath = $null
$AdminEnvPath = $null
$AiArtifactPath = $null
$NodeDir = Join-Path $RootDir '.tools\node'
$NodeExe = Join-Path $NodeDir 'node.exe'
$NpmCli = Join-Path $NodeDir 'node_modules\npm\bin\npm-cli.js'
$Ports = @($UserPort, $AdminPort, $BackendPort, $AiPort)
$NodeVersion = if ($env:LOCAL_NODE_VERSION) { $env:LOCAL_NODE_VERSION } else { '22.15.0' }

function Write-Step {
    param([string]$Message)
    Write-Host ''
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Ensure-Directory {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

function Find-SingleFileParent {
    param(
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
    param([string]$PackageName)

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
    param([switch]$Quiet)

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
                    Write-Host "已停止 $($entry.name) PID $($entry.pid)"
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

function Resolve-SystemPython {
    $candidates = @(
        @{ command = 'py'; arguments = @('-3.12', '-c', 'import sys; print(sys.executable)') },
        @{ command = 'py'; arguments = @('-3.11', '-c', 'import sys; print(sys.executable)') },
        @{ command = 'python'; arguments = @('-c', 'import sys; print(sys.executable)') }
    )

    foreach ($candidate in $candidates) {
        if (-not (Get-Command $candidate.command -ErrorAction SilentlyContinue)) {
            continue
        }

        try {
            $pythonPath = (& $candidate.command @($candidate.arguments) 2>$null | Select-Object -First 1).Trim()
            if ($pythonPath -and (Test-Path -LiteralPath $pythonPath)) {
                return (Resolve-Path -LiteralPath $pythonPath).Path
            }
        }
        catch {
        }
    }

    return $null
}

function Ensure-BootstrapPython {
    $pythonPath = Resolve-SystemPython
    if ($pythonPath) {
        return $pythonPath
    }

    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget) {
        throw 'Python was not found and winget is unavailable. Install Python 3.11 or 3.12, then rerun start-local.ps1.'
    }

    Write-Step 'Python not found. Installing Python 3.12 with winget.'
    & $winget.Source install --id Python.Python.3.12 -e --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        throw 'winget failed to install Python.'
    }

    $pythonPath = Resolve-SystemPython
    if (-not $pythonPath) {
        throw 'Python was installed but python.exe is still not available in the current shell. Reopen PowerShell and try again.'
    }

    return $pythonPath
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

function Ensure-BackendVenv {
    param([string]$BootstrapPython)

    if (Test-Path -LiteralPath $BackendPython) {
        return
    }

    Write-Step 'Creating backend virtual environment'
    Invoke-CommandChecked -Executable $BootstrapPython -Arguments @('-m', 'venv', $VenvDir) -WorkingDirectory $BackendDir
}

function Ensure-BackendDependencies {
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

    if ($importsHealthy) {
        if ($requirementsHash -ne $recordedHash) {
            Set-Content -LiteralPath $stampPath -Value $requirementsHash -Encoding UTF8
        }
        return
    }

    Write-Step 'Installing or updating backend dependencies'
    Invoke-CommandChecked -Executable $BackendPython -Arguments @('-m', 'pip', 'install', '--disable-pip-version-check', '--upgrade', 'pip', 'setuptools', 'wheel') -WorkingDirectory $BackendDir
    Invoke-CommandChecked -Executable $BackendPython -Arguments @('-m', 'pip', 'install', '--disable-pip-version-check', '-r', $BackendRequirements) -WorkingDirectory $BackendDir
    Set-Content -LiteralPath $stampPath -Value $requirementsHash -Encoding UTF8
}

function Ensure-LocalSettings {
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
    Write-Step 'Syncing frontend local environment files'
    $apiUrl = "http://$BindHost`:$BackendPort"
    Set-DotEnvValue -Path $UserEnvPath -Key 'VITE_API_URL' -Value $apiUrl
    Set-DotEnvValue -Path $AdminEnvPath -Key 'VITE_API_URL' -Value $apiUrl
}

function Ensure-LocalNodeRuntime {
    if ((Test-Path -LiteralPath $NodeExe) -and (Test-Path -LiteralPath $NpmCli)) {
        return
    }

    Write-Step 'Installing local Node.js runtime'
    $downloadDir = Join-Path $LocalDevDir 'downloads'
    $zipPath = Join-Path $downloadDir "node-v$NodeVersion-win-x64.zip"
    $extractRoot = Join-Path $downloadDir "node-v$NodeVersion-win-x64"
    $downloadUrl = "https://nodejs.org/dist/v$NodeVersion/node-v$NodeVersion-win-x64.zip"

    Ensure-Directory -Path $downloadDir

    if (-not (Test-Path -LiteralPath $zipPath)) {
        Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath
    }

    if (Test-Path -LiteralPath $extractRoot) {
        Remove-Item -LiteralPath $extractRoot -Recurse -Force
    }

    Expand-Archive -LiteralPath $zipPath -DestinationPath $downloadDir -Force

    if (Test-Path -LiteralPath $NodeDir) {
        Remove-Item -LiteralPath $NodeDir -Recurse -Force
    }

    New-Item -ItemType Directory -Path $NodeDir | Out-Null
    Get-ChildItem -LiteralPath $extractRoot -Force | ForEach-Object {
        Move-Item -LiteralPath $_.FullName -Destination $NodeDir
    }

    if (-not (Test-Path -LiteralPath $NodeExe) -or -not (Test-Path -LiteralPath $NpmCli)) {
        throw 'Local Node.js runtime installation failed.'
    }
}

function Ensure-FrontendDependencies {
    param(
        [string]$FrontendName,
        [string]$FrontendDir
    )

    $lockPath = Join-Path $FrontendDir 'package-lock.json'
    $nodeModulesPath = Join-Path $FrontendDir 'node_modules'
    $stampPath = Join-Path $LocalDevDir "$FrontendName-package-lock.sha256"
    $lockHash = (Get-FileHash -LiteralPath $lockPath -Algorithm SHA256).Hash
    $recordedHash = if (Test-Path -LiteralPath $stampPath) { (Get-Content -LiteralPath $stampPath -Raw).Trim() } else { '' }
    $viteBinary = Join-Path $FrontendDir 'node_modules\.bin\vite.cmd'

    if ((Test-Path -LiteralPath $nodeModulesPath) -and (Test-Path -LiteralPath $viteBinary)) {
        if ($lockHash -ne $recordedHash) {
            Set-Content -LiteralPath $stampPath -Value $lockHash -Encoding UTF8
        }
        return
    }

    Write-Step "Installing $FrontendName frontend dependencies"
    $env:Path = "$NodeDir;$env:Path"
    Invoke-CommandChecked -Executable $NodeExe -Arguments @($NpmCli, 'install', '--no-fund', '--no-audit') -WorkingDirectory $FrontendDir
    Set-Content -LiteralPath $stampPath -Value $lockHash -Encoding UTF8
}

function Ensure-AiModelArtifact {
    if (Test-Path -LiteralPath $AiArtifactPath) {
        return
    }

    Write-Step 'Minimal AI model artifact is missing. Training local baseline model.'
    Invoke-CommandChecked -Executable $BackendPython -Arguments @('train_minimal_baseline.py') -WorkingDirectory $AiDir
}

function Ensure-BackendDatabase {
    Write-Step 'Running Django database initialization'
    $env:DJANGO_SETTINGS_MODULE = 'fake_image_detector.local_settings'
    $env:AI_SERVICE_URL = "http://$BindHost`:$AiPort"
    $env:AI_SERVICE_TIMEOUT = '1200'
    $env:AI_SERVICE_TIMEOUT_SECONDS = '120'
    Invoke-CommandChecked -Executable $BackendPython -Arguments @('manage.py', 'migrate', '--run-syncdb', '--noinput') -WorkingDirectory $BackendDir
}

function Ensure-LocalAdminUser {
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
        name = $Name
        pid = $process.Id
        port = $Port
        healthUrl = $HealthUrl
        stdout = $stdoutPath
        stderr = $stderrPath
    }
}

Write-Step 'Resolving project directories'
$BackendDir = Find-SingleFileParent -Filter 'manage.py' -Description 'backend'
$AiDir = Find-SingleFileParent -Filter 'ai_http_service.py' -Description 'AI service'
$UserFrontendDir = Find-FrontendDirectory -PackageName 'buaa_se'
$AdminFrontendDir = Find-FrontendDirectory -PackageName 'BUAA_SE_manage'
$VenvDir = Join-Path $BackendDir '.venv'
$BackendPython = Join-Path $VenvDir 'Scripts\python.exe'
$BackendRequirements = Join-Path $BackendDir 'requirements.local.txt'
$LocalSettingsPath = Join-Path $BackendDir 'fake_image_detector\local_settings.py'
$UserEnvPath = Join-Path $UserFrontendDir '.env'
$AdminEnvPath = Join-Path $AdminFrontendDir '.env'
$AiArtifactPath = Join-Path $AiDir 'detection_service\artifacts\minimal_baseline.pkl'

Write-Step 'Preparing local working directories'
Ensure-Directory -Path $LocalDevDir
Ensure-Directory -Path $LogsDir

Write-Step 'Stopping existing local service processes'
Stop-ManagedProcesses -Quiet

Write-Step 'Checking Python environment'
$bootstrapPython = Ensure-BootstrapPython
Ensure-BackendVenv -BootstrapPython $bootstrapPython
Ensure-BackendDependencies

Write-Step 'Checking Node.js environment'
Ensure-LocalNodeRuntime

Ensure-LocalSettings
Ensure-FrontendEnvFiles
Ensure-FrontendDependencies -FrontendName 'user' -FrontendDir $UserFrontendDir
Ensure-FrontendDependencies -FrontendName 'admin' -FrontendDir $AdminFrontendDir
Ensure-AiModelArtifact
Ensure-BackendDatabase
Ensure-LocalAdminUser

Write-Step 'Starting local services'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
$env:AI_SERVICE_TIMEOUT_SECONDS = '120'
$aiProcess = Start-ManagedProcess -Name 'ai-service' -Executable $BackendPython -Arguments @('ai_http_service.py', '--host', $BindHost, '--port', "$AiPort") -WorkingDirectory $AiDir -HealthUrl "http://$BindHost`:$AiPort/health" -Port $AiPort -TimeoutSeconds 120

$env:DJANGO_SETTINGS_MODULE = 'fake_image_detector.local_settings'
$env:AI_SERVICE_URL = "http://$BindHost`:$AiPort"
$env:AI_SERVICE_TIMEOUT = '1200'
$backendProcess = Start-ManagedProcess -Name 'django' -Executable $BackendPython -Arguments @('manage.py', 'runserver', "$BindHost`:$BackendPort") -WorkingDirectory $BackendDir -HealthUrl "http://$BindHost`:$BackendPort/admin/" -Port $BackendPort -TimeoutSeconds 120

$env:Path = "$NodeDir;$env:Path"
$userProcess = Start-ManagedProcess -Name 'frontend-user' -Executable $NodeExe -Arguments @($NpmCli, 'run', 'dev', '--', '--host', $BindHost, '--port', "$UserPort", '--strictPort') -WorkingDirectory $UserFrontendDir -HealthUrl "http://$BindHost`:$UserPort/" -Port $UserPort -TimeoutSeconds 120
$adminProcess = Start-ManagedProcess -Name 'frontend-admin' -Executable $NodeExe -Arguments @($NpmCli, 'run', 'dev', '--', '--host', $BindHost, '--port', "$AdminPort", '--strictPort') -WorkingDirectory $AdminFrontendDir -HealthUrl "http://$BindHost`:$AdminPort/" -Port $AdminPort -TimeoutSeconds 120

$state = @($aiProcess, $backendProcess, $userProcess, $adminProcess)
$state | ConvertTo-Json | Set-Content -LiteralPath $StatePath -Encoding UTF8

Write-Host ''
Write-Host 'Local validation environment is ready:' -ForegroundColor Green
Write-Host "  User frontend:  http://$BindHost`:$UserPort"
Write-Host "  Admin frontend: http://$BindHost`:$AdminPort"
Write-Host "  Django:   http://$BindHost`:$BackendPort/admin/"
Write-Host "  AI service: http://$BindHost`:$AiPort/health"
Write-Host ''
Write-Host "Local admin: $AdminUser / $AdminPassword"
Write-Host "Logs: $LogsDir"
Write-Host "Stop with: .\stop-local.ps1"
