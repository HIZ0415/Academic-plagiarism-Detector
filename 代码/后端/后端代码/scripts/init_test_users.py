"""
创建本地测试用户
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fake_image_detector.local_settings')

import django
django.setup()

from core.models import User, Organization

# 创建组织
org, _ = Organization.objects.get_or_create(
    name='Local Demo Organization',
    defaults={'email': 'local-org@example.com'}
)

# 创建管理员用户
admin_user, created = User.objects.get_or_create(
    email='admin@mail.com',
    defaults={
        'username': 'admin',
        'role': 'admin',
        'organization': org,
    }
)
if created:
    admin_user.set_password('Admin123!')
    admin_user.save()
    print(f'✓ 创建管理员: admin@mail.com / Admin123!')
else:
    print('✓ 管理员已存在')

# 创建发布者（编辑）用户
publisher_user, created = User.objects.get_or_create(
    email='publisher_test@example.com',
    defaults={
        'username': 'publisher_test',
        'role': 'publisher',
        'organization': org,
    }
)
if created:
    publisher_user.set_password('Publisher123!')
    publisher_user.save()
    print(f'✓ 创建发布者: publisher_test@example.com / Publisher123!')
else:
    print('✓ 发布者已存在')

# 创建审稿人（专家）用户
reviewer_user, created = User.objects.get_or_create(
    email='reviewer_test@example.com',
    defaults={
        'username': 'reviewer_test',
        'role': 'reviewer',
        'organization': org,
    }
)
if created:
    reviewer_user.set_password('Reviewer123!')
    reviewer_user.save()
    print(f'✓ 创建审稿人: reviewer_test@example.com / Reviewer123!')
else:
    print('✓ 审稿人已存在')

print('\n所有测试用户已准备就绪！')
