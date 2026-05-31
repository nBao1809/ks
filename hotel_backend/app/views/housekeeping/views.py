from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from app.models import UserRole
from app.core.pagination import StandardPagination
from app.permissions import IsHousekeeping, IsManagerOrReceptionist
from app.core.schema import PARAM_PAGE, PARAM_PAGE_SIZE, TAG_HOUSEKEEPING
from app.models import HousekeepingTask
from app.serializers.housekeeping import (
    HousekeepingLogSerializer,
    HousekeepingTaskAssignSerializer,
    HousekeepingTaskCreateSerializer,
    HousekeepingTaskSerializer,
    HousekeepingTaskUpdateSerializer,
)
from app.views.housekeeping.services.task_service import HousekeepingTaskService


HK_LIST_PARAMS = [
    PARAM_PAGE,
    PARAM_PAGE_SIZE,
    OpenApiParameter(name='status', type=str, location=OpenApiParameter.QUERY, required=False),
    OpenApiParameter(name='assigned_to', type=str, location=OpenApiParameter.QUERY, required=False, description='me | unassigned'),
    OpenApiParameter(name='priority', type=str, location=OpenApiParameter.QUERY, required=False),
    OpenApiParameter(name='floor', type=int, location=OpenApiParameter.QUERY, required=False),
]


@extend_schema_view(
    get=extend_schema(tags=[TAG_HOUSEKEEPING], summary='Danh sách task dọn phòng', parameters=HK_LIST_PARAMS, responses={200: HousekeepingTaskSerializer(many=True)}),
    post=extend_schema(tags=[TAG_HOUSEKEEPING], summary='Tạo task', request=HousekeepingTaskCreateSerializer, responses={201: HousekeepingTaskSerializer}),
)
class HousekeepingTaskListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        assigned = request.query_params.get('assigned_to')
        qs = HousekeepingTaskService.queryset_for_user(
            request.user,
            assigned_to_me=(assigned == 'me'),
            unassigned=(assigned == 'unassigned'),
        )
        status_param = request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)
        priority = request.query_params.get('priority')
        if priority:
            qs = qs.filter(priority=priority)
        floor = request.query_params.get('floor')
        if floor:
            qs = qs.filter(room__floor=floor)
        qs = qs.order_by('-created_at')
        paginator = StandardPagination()
        page_data = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(HousekeepingTaskSerializer(page_data, many=True).data)

    def post(self, request):
        if request.user.role not in (UserRole.MANAGER, UserRole.RECEPTIONIST) and not request.user.is_superuser:
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = HousekeepingTaskCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        task = HousekeepingTaskService.create_task(
            d['room_id'], d.get('assigned_to_id'), d.get('priority'), d.get('task_type'), d.get('notes', ''), request.user,
        )
        return Response(HousekeepingTaskSerializer(task).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    patch=extend_schema(tags=[TAG_HOUSEKEEPING], summary='Cập nhật task', request=HousekeepingTaskUpdateSerializer, responses={200: HousekeepingTaskSerializer}),
)
class HousekeepingTaskDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        serializer = HousekeepingTaskUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        if 'status' in serializer.validated_data:
            note = serializer.validated_data.get('notes', '') or ''
            task = HousekeepingTaskService.update_status(pk, serializer.validated_data['status'], request.user, note=note)
        else:
            task = get_object_or_404(HousekeepingTaskService.queryset_for_user(request.user), pk=pk)
            if 'notes' in request.data:
                task.notes = request.data['notes']
                task.save(update_fields=['notes', 'updated_at'])
        return Response(HousekeepingTaskSerializer(task).data)


@extend_schema_view(
    post=extend_schema(tags=[TAG_HOUSEKEEPING], summary='Giao task', request=HousekeepingTaskAssignSerializer, responses={200: HousekeepingTaskSerializer}),
)
class HousekeepingTaskAssignView(APIView):
    permission_classes = [IsManagerOrReceptionist]

    def post(self, request, pk):
        serializer = HousekeepingTaskAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = HousekeepingTaskService.assign(pk, serializer.validated_data['assigned_to_id'], request.user)
        return Response(HousekeepingTaskSerializer(task).data)


@extend_schema_view(
    get=extend_schema(tags=[TAG_HOUSEKEEPING], summary='Lịch sử task', responses={200: HousekeepingLogSerializer(many=True)}),
)
class HousekeepingTaskLogView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        task = get_object_or_404(HousekeepingTaskService.queryset_for_user(request.user), pk=pk)
        logs = task.logs.select_related('performed_by')
        return Response(HousekeepingLogSerializer(logs, many=True).data)


@extend_schema_view(
    get=extend_schema(
        tags=[TAG_HOUSEKEEPING],
        summary='Lịch sử dọn phòng theo phòng',
        parameters=[
            OpenApiParameter(name='room_id', type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name='from', type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name='to', type=str, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={200: HousekeepingTaskSerializer(many=True)},
    ),
)
class HousekeepingHistoryView(APIView):
    permission_classes = [IsManagerOrReceptionist]

    def get(self, request):
        qs = HousekeepingTask.objects.select_related('room', 'assigned_to').filter(status='completed', is_active=True)
        room_id = request.query_params.get('room_id')
        if room_id:
            qs = qs.filter(room_id=room_id)
        return Response(HousekeepingTaskSerializer(qs.order_by('-completed_at')[:50], many=True).data)




