param(
  [string]$DjangoSettings = "fake_image_detector.cloud_settings",
  [switch]$CreateAdmin = $false,
  [string]$AdminUsername = "admin",
  [string]$AdminEmail = "admin@example.com",
  [string]$AdminPassword = ""
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (!(Test-Path ".\.venv\Scripts\python.exe")) {
  throw "Python virtualenv not found: .venv/Scripts/python.exe"
}

$env:DJANGO_SETTINGS_MODULE = $DjangoSettings

Write-Host "[prepare_cloud_db] DJANGO_SETTINGS_MODULE=$DjangoSettings"
Write-Host "[prepare_cloud_db] Running django checks..."
& ".\.venv\Scripts\python.exe" manage.py check

Write-Host "[prepare_cloud_db] Applying base schema..."
& ".\.venv\Scripts\python.exe" manage.py migrate --run-syncdb

Write-Host "[prepare_cloud_db] Applying DetectionTask v2 schema patch..."
& ".\.venv\Scripts\python.exe" manage.py migrate_detection_task_v2

Write-Host "[prepare_cloud_db] Backfilling DetectionTask v2 data..."
& ".\.venv\Scripts\python.exe" manage.py backfill_detection_task_v2

Write-Host "[prepare_cloud_db] Collecting static files..."
& ".\.venv\Scripts\python.exe" manage.py collectstatic --noinput

if ($CreateAdmin) {
  if ([string]::IsNullOrWhiteSpace($AdminPassword)) {
    throw "When -CreateAdmin is enabled, -AdminPassword must be provided."
  }
  $env:DJANGO_SUPERUSER_USERNAME = $AdminUsername
  $env:DJANGO_SUPERUSER_EMAIL = $AdminEmail
  $env:DJANGO_SUPERUSER_PASSWORD = $AdminPassword
  Write-Host "[prepare_cloud_db] Creating/updating superuser..."
  & ".\.venv\Scripts\python.exe" manage.py shell -c "from django.contrib.auth import get_user_model; U=get_user_model(); u,created=U.objects.get_or_create(username='$AdminUsername', defaults={'email':'$AdminEmail'}); u.email='$AdminEmail'; u.is_superuser=True; u.is_staff=True; u.is_active=True; u.role='admin'; u.set_password('$AdminPassword'); u.save(); print('superuser_ready', u.username, created)"
}

Write-Host "[prepare_cloud_db] Done."

