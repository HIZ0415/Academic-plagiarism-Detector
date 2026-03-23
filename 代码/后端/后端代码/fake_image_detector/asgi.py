"""
ASGI config for fake_image_detector project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from . routings import websocket_urlpatterns
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fake_image_detector.settings")
django.setup()

# application = get_asgi_application()
application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),  # 加载 WebSocket 路由
    }
)