"""Sync local sqlite demo users to a canonical state."""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fake_image_detector.local_settings')

import django

django.setup()

from core.models import Organization, User


def ensure_org() -> Organization:
    org, created = Organization.objects.get_or_create(
        name='Local Demo Organization',
        defaults={'email': 'local-org@example.com'},
    )
    changed = False
    if org.email != 'local-org@example.com':
        org.email = 'local-org@example.com'
        changed = True
    if changed:
        org.save(update_fields=['email'])
    print(f"{'created' if created else 'synced'} organization: {org.name} / {org.email}")
    return org


def sync_user(
    *,
    email: str,
    username: str,
    role: str,
    password: str,
    organization: Organization,
    is_staff: bool,
    is_superuser: bool,
) -> None:
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            'username': username,
            'role': role,
            'organization': organization,
            'is_staff': is_staff,
            'is_superuser': is_superuser,
        },
    )

    changed_fields = []
    if user.username != username:
        user.username = username
        changed_fields.append('username')
    if user.role != role:
        user.role = role
        changed_fields.append('role')
    if user.organization_id != organization.id:
        user.organization = organization
        changed_fields.append('organization')
    if user.is_staff != is_staff:
        user.is_staff = is_staff
        changed_fields.append('is_staff')
    if user.is_superuser != is_superuser:
        user.is_superuser = is_superuser
        changed_fields.append('is_superuser')

    user.set_password(password)
    user.save()

    if created:
      action = 'created'
    elif changed_fields:
      action = f"updated ({', '.join(changed_fields)})"
    else:
      action = 'reset password'
    print(f"{action} user: {email} / {password} / role={role}")


def main() -> None:
    org = ensure_org()
    sync_user(
        email='admin@mail.com',
        username='admin',
        role='admin',
        password='Admin123!',
        organization=org,
        is_staff=True,
        is_superuser=True,
    )
    sync_user(
        email='publisher_test@example.com',
        username='publisher_test',
        role='publisher',
        password='Publisher123!',
        organization=org,
        is_staff=False,
        is_superuser=False,
    )
    sync_user(
        email='reviewer_test@example.com',
        username='reviewer_test',
        role='reviewer',
        password='Reviewer123!',
        organization=org,
        is_staff=False,
        is_superuser=False,
    )
    print('\nlocal sqlite test users are now synchronized.')


if __name__ == '__main__':
    main()
