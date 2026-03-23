from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# 设置默认的Django设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fake_image_detector.settings')

app = Celery('fake_image_detector')

# 使用Django的配置文件作为Celery的配置
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现所有已注册的应用中的任务
app.autodiscover_tasks()


# 配置 Celery 使用 solo 任务池  仅在windows系统
app.conf.update(
    worker_pool='solo',
)