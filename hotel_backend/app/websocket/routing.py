from django.urls import re_path

from app.websocket.consumers import HousekeepingConsumer

websocket_urlpatterns = [
    re_path(r'^ws/housekeeping/$', HousekeepingConsumer.as_asgi()),
]
