from django.urls import re_path, path
from . import consumers

websocket_urlpatterns = [
    re_path(
        r'ws/task/(?P<task_id>\d+)/$',  # WebSocket 地址格式，例如 ws://domain/ws/task/123/
        consumers.TaskConsumer.as_asgi()
    ),
    re_path(r'ws/notifications/', consumers.NotificationConsumer.as_asgi()),
]