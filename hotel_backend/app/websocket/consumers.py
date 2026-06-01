import json

from channels.generic.websocket import AsyncWebsocketConsumer


class HousekeepingConsumer(AsyncWebsocketConsumer):
    GROUP_NAME = 'housekeeping'

    async def connect(self):
        await self.channel_layer.group_add(self.GROUP_NAME, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.GROUP_NAME, self.channel_name)

    # Nhận event từ channel layer và forward xuống client
    async def housekeeping_task_update(self, event):
        await self.send(text_data=json.dumps({'type': 'task_update'}))
