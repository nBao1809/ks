from django.db import connection
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from app.core.schema import TAG_HEALTH


class HealthResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    database = serializers.CharField()


@extend_schema(
    tags=[TAG_HEALTH],
    summary='Health check',
    responses={200: HealthResponseSerializer},
    auth=[],
)
class HealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        db_ok = True
        try:
            connection.ensure_connection()
        except Exception:
            db_ok = False
        return Response({
            'status': 'ok' if db_ok else 'degraded',
            'database': 'ok' if db_ok else 'error',
        })
