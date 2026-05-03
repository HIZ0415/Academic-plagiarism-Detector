param(
  [string]$DjangoSettings = "fake_image_detector.local_settings"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (!(Test-Path ".\.venv\Scripts\python.exe")) {
  throw "Python virtualenv not found: .venv/Scripts/python.exe"
}

$env:DJANGO_SETTINGS_MODULE = $DjangoSettings

Write-Host "[migrate_detection_task_v2] DJANGO_SETTINGS_MODULE=$DjangoSettings"
& ".\.venv\Scripts\python.exe" manage.py migrate_detection_task_v2
