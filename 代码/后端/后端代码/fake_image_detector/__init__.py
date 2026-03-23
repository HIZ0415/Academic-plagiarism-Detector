# fake_image_detector/__init__.py
from __future__ import absolute_import, unicode_literals

import pymysql

pymysql.install_as_MySQLdb()

# 防止django启动时加载Celery
from .celery import app as celery_app

__all__ = ('celery_app',)

