from datetime import datetime

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from app.core.pagination import StandardPagination
from app.core.schema import PARAM_PAGE, PARAM_PAGE_SIZE, PARAM_SEARCH, TAG_AMENITIES, TAG_ROOMS, TAG_ROOM_TYPES
from app.models import Amenity, Room, RoomPrice, RoomType, RoomTypeImage
from app.permissions import AmenityPermission, RoomPermission, RoomStatusPermission
from app.rooms.schema_docs import AvailabilityResponseSerializer
from app.serializers.rooms import (
    AmenitySerializer,
    AmenityWriteSerializer,
    RoomDetailSerializer,
    RoomListSerializer,
    RoomPriceSerializer,
    RoomPriceWriteSerializer,
    RoomStatusUpdateSerializer,
    RoomTypeDetailSerializer,
    RoomTypeImageSerializer,
    RoomTypeImageWriteSerializer,
    RoomTypeListSerializer,
    RoomTypeWriteSerializer,
    RoomWriteSerializer,
)
from app.views.rooms.services.room_service import RoomService

AVAILABILITY_PARAMS = [
    OpenApiParameter(name='check_in', type=str, location=OpenApiParameter.QUERY, required=True, description='YYYY-MM-DD'),
    OpenApiParameter(name='check_out', type=str, location=OpenApiParameter.QUERY, required=True, description='YYYY-MM-DD'),
    OpenApiParameter(name='adults', type=int, location=OpenApiParameter.QUERY, required=False, description='Mặc định 1'),
    OpenApiParameter(name='children', type=int, location=OpenApiParameter.QUERY, required=False, description='Mặc định 0'),
    OpenApiParameter(name='room_type_id', type=str, location=OpenApiParameter.QUERY, required=False, description='UUID loại phòng'),
]

ROOM_LIST_PARAMS = [
    PARAM_PAGE,
    PARAM_PAGE_SIZE,
    OpenApiParameter(name='status', type=str, location=OpenApiParameter.QUERY, required=False),
    OpenApiParameter(name='floor', type=int, location=OpenApiParameter.QUERY, required=False),
    OpenApiParameter(name='room_type_id', type=str, location=OpenApiParameter.QUERY, required=False),
]

ROOM_TYPE_LIST_PARAMS = [
    PARAM_PAGE,
    PARAM_PAGE_SIZE,
    PARAM_SEARCH,
    OpenApiParameter(name='ordering', type=str, location=OpenApiParameter.QUERY, required=False),
]


@extend_schema_view(
    get=extend_schema(
        tags=[TAG_ROOM_TYPES],
        summary='Danh sách loại phòng',
        parameters=ROOM_TYPE_LIST_PARAMS,
        responses={200: RoomTypeListSerializer(many=True)},
    ),
    post=extend_schema(
        tags=[TAG_ROOM_TYPES],
        summary='Tạo loại phòng',
        request=RoomTypeWriteSerializer,
        responses={201: RoomTypeDetailSerializer},
    ),
)
class RoomTypeListCreateView(APIView):
    permission_classes = [RoomPermission]

    def get(self, request):
        qs = RoomType.objects.filter(is_active=True).prefetch_related('amenities', 'images')
        search = request.query_params.get('search')
        if search:
            qs = qs.filter(name__icontains=search)
        ordering = request.query_params.get('ordering', 'name')
        qs = qs.order_by(ordering)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = RoomTypeListSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = RoomTypeWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            RoomTypeDetailSerializer(instance, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    get=extend_schema(tags=[TAG_ROOM_TYPES], summary='Chi tiết loại phòng', responses={200: RoomTypeDetailSerializer}),
    patch=extend_schema(tags=[TAG_ROOM_TYPES], summary='Cập nhật loại phòng', request=RoomTypeWriteSerializer, responses={200: RoomTypeDetailSerializer}),
    delete=extend_schema(tags=[TAG_ROOM_TYPES], summary='Xóa loại phòng (soft)', responses={204: None}),
)
class RoomTypeDetailView(APIView):
    permission_classes = [RoomPermission]

    def get(self, request, pk):
        instance = get_object_or_404(RoomType.objects.prefetch_related('amenities', 'images', 'prices'), pk=pk)
        return Response(RoomTypeDetailSerializer(instance, context={'request': request}).data)

    def patch(self, request, pk):
        instance = get_object_or_404(RoomType, pk=pk)
        serializer = RoomTypeWriteSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(RoomTypeDetailSerializer(instance, context={'request': request}).data)

    def delete(self, request, pk):
        instance = get_object_or_404(RoomType, pk=pk)
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    get=extend_schema(tags=[TAG_ROOM_TYPES], summary='Danh sách ảnh loại phòng', responses={200: RoomTypeImageSerializer(many=True)}),
    post=extend_schema(
        tags=[TAG_ROOM_TYPES],
        summary='Upload ảnh loại phòng',
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'image': {'type': 'string', 'format': 'binary'},
                    'is_primary': {'type': 'boolean'},
                    'sort_order': {'type': 'integer'},
                },
                'required': ['image'],
            },
        },
        responses={201: RoomTypeImageSerializer},
    ),
)
class RoomTypeImageView(APIView):
    permission_classes = [RoomPermission]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, pk):
        images = RoomTypeImage.objects.filter(room_type_id=pk, is_active=True)
        return Response(RoomTypeImageSerializer(images, many=True, context={'request': request}).data)

    def post(self, request, pk):
        get_object_or_404(RoomType, pk=pk)
        serializer = RoomTypeImageWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(room_type_id=pk)
        if instance.is_primary:
            RoomTypeImage.objects.filter(room_type_id=pk).exclude(pk=instance.pk).update(is_primary=False)
        return Response(
            RoomTypeImageSerializer(instance, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    get=extend_schema(tags=[TAG_ROOM_TYPES], summary='Danh sách giá theo mùa', responses={200: RoomPriceSerializer(many=True)}),
    post=extend_schema(tags=[TAG_ROOM_TYPES], summary='Thêm giá theo mùa', request=RoomPriceWriteSerializer, responses={201: RoomPriceSerializer}),
)
class RoomTypePriceView(APIView):
    permission_classes = [RoomPermission]

    def get(self, request, pk):
        prices = RoomPrice.objects.filter(room_type_id=pk, is_active=True)
        return Response(RoomPriceSerializer(prices, many=True).data)

    def post(self, request, pk):
        get_object_or_404(RoomType, pk=pk)
        serializer = RoomPriceWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(room_type_id=pk)
        return Response(RoomPriceSerializer(instance).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(tags=[TAG_ROOMS], summary='Danh sách phòng', parameters=ROOM_LIST_PARAMS, responses={200: RoomListSerializer(many=True)}),
    post=extend_schema(tags=[TAG_ROOMS], summary='Tạo phòng', request=RoomWriteSerializer, responses={201: RoomDetailSerializer}),
)
class RoomListCreateView(APIView):
    permission_classes = [RoomPermission]

    def get(self, request):
        qs = Room.objects.select_related('room_type').filter(is_active=True)
        status_param = request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)
        floor = request.query_params.get('floor')
        if floor:
            qs = qs.filter(floor=floor)
        room_type_id = request.query_params.get('room_type_id')
        if room_type_id:
            qs = qs.filter(room_type_id=room_type_id)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = RoomListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = RoomWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(RoomDetailSerializer(instance).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(tags=[TAG_ROOMS], summary='Chi tiết phòng', responses={200: RoomDetailSerializer}),
    patch=extend_schema(tags=[TAG_ROOMS], summary='Cập nhật phòng', request=RoomWriteSerializer, responses={200: RoomDetailSerializer}),
    delete=extend_schema(tags=[TAG_ROOMS], summary='Xóa phòng (soft)', responses={204: None}),
)
class RoomDetailView(APIView):
    permission_classes = [RoomPermission]

    def get(self, request, pk):
        instance = get_object_or_404(Room.objects.select_related('room_type'), pk=pk)
        return Response(RoomDetailSerializer(instance).data)

    def patch(self, request, pk):
        instance = get_object_or_404(Room, pk=pk)
        serializer = RoomWriteSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(RoomDetailSerializer(instance).data)

    def delete(self, request, pk):
        instance = get_object_or_404(Room, pk=pk)
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    patch=extend_schema(
        tags=[TAG_ROOMS],
        summary='Cập nhật trạng thái phòng',
        request=RoomStatusUpdateSerializer,
        responses={200: RoomDetailSerializer},
    ),
)
class RoomStatusUpdateView(APIView):
    permission_classes = [RoomStatusPermission]

    def patch(self, request, pk):
        instance = get_object_or_404(Room, pk=pk)
        serializer = RoomStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.check_object_permissions(request, instance)
        room = RoomService.update_room_status(
            instance,
            serializer.validated_data['status'],
            notes=serializer.validated_data.get('notes'),
            user=request.user,
        )
        return Response(RoomDetailSerializer(room).data)


@extend_schema_view(
    get=extend_schema(
        tags=[TAG_ROOMS],
        summary='Kiểm tra phòng trống',
        description='Truyền check_in, check_out qua query string.',
        parameters=AVAILABILITY_PARAMS,
        responses={200: AvailabilityResponseSerializer},
    ),
)
class AvailabilityView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        check_in = request.query_params.get('check_in')
        check_out = request.query_params.get('check_out')
        if not check_in or not check_out:
            return Response(
                {'check_in': ['Bắt buộc'], 'check_out': ['Bắt buộc']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
            check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'detail': 'Ngày không hợp lệ. Định dạng đúng: YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        adults = int(request.query_params.get('adults', 1))
        children = int(request.query_params.get('children', 0))
        room_type_id = request.query_params.get('room_type_id')
        data = RoomService.check_availability(
            check_in_date, check_out_date, adults, children, room_type_id,
        )
        return Response(data)


@extend_schema_view(
    get=extend_schema(tags=[TAG_AMENITIES], summary='Danh sách tiện nghi', responses={200: AmenitySerializer(many=True)}),
    post=extend_schema(tags=[TAG_AMENITIES], summary='Tạo tiện nghi', request=AmenityWriteSerializer, responses={201: AmenitySerializer}),
)
class AmenityListCreateView(APIView):
    permission_classes = [AmenityPermission]

    def get(self, request):
        qs = Amenity.objects.filter(is_active=True)
        return Response(AmenitySerializer(qs, many=True).data)

    def post(self, request):
        serializer = AmenityWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(AmenitySerializer(instance).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    patch=extend_schema(tags=[TAG_AMENITIES], summary='Cập nhật tiện nghi', request=AmenityWriteSerializer, responses={200: AmenitySerializer}),
    delete=extend_schema(tags=[TAG_AMENITIES], summary='Xóa tiện nghi (soft)', responses={204: None}),
)
class AmenityDetailView(APIView):
    permission_classes = [AmenityPermission]

    def patch(self, request, pk):
        instance = get_object_or_404(Amenity, pk=pk)
        serializer = AmenityWriteSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(AmenitySerializer(instance).data)

    def delete(self, request, pk):
        instance = get_object_or_404(Amenity, pk=pk)
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)




