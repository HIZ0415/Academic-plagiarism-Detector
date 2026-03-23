from channels.generic.websocket import AsyncWebsocketConsumer
import json

class TaskConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # 从前端连接 URL 中获取任务 ID
        self.task_id = self.scope['url_route']['kwargs']['task_id']
        self.group_name = f'task_{self.task_id}'  # 定义频道组名

        # 将当前连接加入频道组
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # 断开连接时退出频道组
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    # 接收频道组的消息并转发给前端
    async def task_status_update(self, event):
        await self.send(text_data=json.dumps(event['message']))


import json
from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework_simplejwt.tokens import AccessToken
from core.models import User
from channels.db import database_sync_to_async
from urllib.parse import parse_qs

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # 从 URL 查询参数中获取 token
        query_params = self.scope['query_string'].decode('utf-8')
        params = parse_qs(query_params)
        token = params.get('token', [None])[0]  # 获取 token 参数

        if token:
            try:
                access_token = AccessToken(token)  # 尝试解码 JWT token
                user_id = access_token['user_id']
                self.user = await self.get_user(user_id)
                group_name = f"user_{self.user.id}_notifications"
                # 加入 WebSocket 群组
                await self.channel_layer.group_add(
                    group_name,
                    self.channel_name
                )
                await self.accept()
            except Exception as e:
                print(f"Error: {e}")
                await self.close()
        else:
            await self.close()

    @database_sync_to_async
    def get_user(self, user_id):
        return User.objects.get(id=user_id)

    async def disconnect(self, close_code):
        # 断开连接时的处理逻辑
        pass

    async def send_notification(self, message):
        # 发送通知给 WebSocket 客户端
        await self.send(text_data=json.dumps({
            'message': message
        }))
