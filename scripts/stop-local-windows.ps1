[CmdletBinding()]
param(
    [int[]]$Ports = @(3000, 3001, 8000, 8010)
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

function Write-Step {
    param([string]$Message)
    Write-Host ''
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Assert-WindowsPlatform {
    if ([System.Environment]::OSVersion.Platform -ne [System.PlatformID]::Win32NT) {
        throw 'This script is Windows-only.'
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

function Stop-ProcessId {
    param([int]$ProcessId)

    try {
        Stop-Process -Id $ProcessId -Force -ErrorAction Stop
        Write-Host "Stopped PID $ProcessId"
    }
    catch {
    }
}

Assert-WindowsPlatform

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Resolve-RepositoryRoot -StartDir $ScriptDir
$StatePath = Join-Path $RootDir '.local-dev\processes.json'

Write-Step 'Stopping processes recorded by the local state file'
if (Test-Path -LiteralPath $StatePath) {
    try {
        $state = Get-Content -LiteralPath $StatePath -Raw | ConvertFrom-Json
    }
    catch {
        $state = @()
    }

    foreach ($entry in @($state)) {
        if ($null -ne $entry -and $entry.pid) {
            Stop-ProcessId -ProcessId ([int]$entry.pid)
        }
    }

    Remove-Item -LiteralPath $StatePath -Force
}

Write-Step 'Cleaning up any remaining listeners on known ports'
foreach ($port in $Ports) {
    foreach ($processId in (Get-PortProcessIds -Port $port)) {
        Stop-ProcessId -ProcessId $processId
    }
}

Write-Host ''
Write-Host 'Local services have been stopped.' -ForegroundColor Green
