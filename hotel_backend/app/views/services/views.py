from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from app.models import UserRole
from app.core.pagination import StandardPagination
from app.permissions import IsManager, IsManagerOrReceptionist
from app.core.schema import PARAM_PAGE, PARAM_PAGE_SIZE, TAG_SERVICES
from app.models import Service, ServiceCategory
from app.serializers.services import (
    ServiceCategorySerializer,
    ServiceOrderCreateSerializer,
    ServiceCategoryWriteSerializer,
    ServiceOrderSerializer,
    ServiceSerializer,
    ServiceWriteSerializer,
)
from app.views.services.services.order_service import ServiceOrderService


@extend_schema_view(
    get=extend_schema(tags=[TAG_SERVICES], summary='Danh mục dịch vụ', responses={200: ServiceCategorySerializer(many=True)}),
    post=extend_schema(
        tags=[TAG_SERVICES],
        summary='Tạo danh mục dịch vụ (Manager)',
        request=ServiceCategoryWriteSerializer,
        responses={201: ServiceCategorySerializer},
    ),
)
class ServiceCategoryListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsManager()]
        return [IsAuthenticated()]

    def get(self, request):
        qs = ServiceCategory.objects.filter(is_active=True).order_by('name')
        return Response(ServiceCategorySerializer(qs, many=True).data)

    def post(self, request):
        serializer = ServiceCategoryWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(ServiceCategorySerializer(instance).data, status=status.HTTP_201_CREATED)

@extend_schema_view(
    get=extend_schema(
        tags=[TAG_SERVICES],
        summary='Danh sách dịch vụ',
        parameters=[
            OpenApiParameter(name='category_id', type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name='is_active', type=bool, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={200: ServiceSerializer(many=True)},
    ),
    post=extend_schema(tags=[TAG_SERVICES], summary='Tạo dịch vụ (Manager)', request=ServiceWriteSerializer, responses={201: ServiceSerializer}),
)
class ServiceListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsManager()]
        return [IsAuthenticated()]

    def get(self, request):
        qs = Service.objects.select_related('category').filter(is_active=True)
        category_id = request.query_params.get('category_id')
        if category_id:
            qs = qs.filter(category_id=category_id)
        include_staff = request.query_params.get('include_staff_only', '').lower() in ('1', 'true', 'yes')
        is_staff = request.user.is_superuser or request.user.role in (
            UserRole.MANAGER, UserRole.RECEPTIONIST,
        )
        if not include_staff or not is_staff:
            qs = qs.filter(is_staff_only=False)
        return Response(ServiceSerializer(qs, many=True).data)

    def post(self, request):
        serializer = ServiceWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(ServiceSerializer(instance).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    patch=extend_schema(tags=[TAG_SERVICES], summary='Cập nhật dịch vụ', request=ServiceWriteSerializer, responses={200: ServiceSerializer}),
    delete=extend_schema(tags=[TAG_SERVICES], summary='Xóa dịch vụ (soft)', responses={204: None}),
)
class ServiceDetailView(APIView):
    permission_classes = [IsManager]

    def patch(self, request, pk):
        instance = get_object_or_404(Service, pk=pk)
        serializer = ServiceWriteSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(ServiceSerializer(instance).data)

    def delete(self, request, pk):
        instance = get_object_or_404(Service, pk=pk)
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    get=extend_schema(tags=[TAG_SERVICES], summary='Danh sách đơn dịch vụ', parameters=[PARAM_PAGE, PARAM_PAGE_SIZE], responses={200: ServiceOrderSerializer(many=True)}),
    post=extend_schema(tags=[TAG_SERVICES], summary='Đặt dịch vụ', request=ServiceOrderCreateSerializer, responses={201: ServiceOrderSerializer}),
)
class ServiceOrderListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = ServiceOrderService.queryset_for_user(request.user)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs.order_by('-created_at'), request)
        return paginator.get_paginated_response(ServiceOrderSerializer(page, many=True).data)

    def post(self, request):
        serializer = ServiceOrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        order = ServiceOrderService.create_order(
            request.user,
            data['booking_id'],
            data['items'],
            scheduled_at=data.get('scheduled_at'),
            note=data.get('note', ''),
        )
        return Response(ServiceOrderSerializer(order).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(tags=[TAG_SERVICES], summary='Chi tiết đơn dịch vụ', responses={200: ServiceOrderSerializer}),
)
class ServiceOrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        order = get_object_or_404(ServiceOrderService.queryset_for_user(request.user), pk=pk)
        return Response(ServiceOrderSerializer(order).data)


@extend_schema_view(
    post=extend_schema(tags=[TAG_SERVICES], summary='Xác nhận đơn dịch vụ', responses={200: ServiceOrderSerializer}),
)
class ServiceOrderConfirmView(APIView):
    permission_classes = [IsManagerOrReceptionist]

    def post(self, request, pk):
        order = ServiceOrderService.confirm(pk, request.user)
        return Response(ServiceOrderSerializer(order).data)


@extend_schema_view(
    get=extend_schema(tags=[TAG_SERVICES], summary='Đơn dịch vụ theo booking', responses={200: ServiceOrderSerializer(many=True)}),
)
class BookingServiceOrdersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, booking_id):
        qs = ServiceOrderService.queryset_for_user(request.user).filter(booking_id=booking_id)
        return Response(ServiceOrderSerializer(qs, many=True).data)


@extend_schema_view(
    post=extend_schema(tags=[TAG_SERVICES], summary='Hủy đơn dịch vụ', responses={200: ServiceOrderSerializer}),
)
class ServiceOrderCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        order = ServiceOrderService.cancel(pk, request.user)
        return Response(ServiceOrderSerializer(order).data)




