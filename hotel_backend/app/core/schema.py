from drf_spectacular.utils import OpenApiParameter
from rest_framework import serializers

from app.serializers.accounts import (
    ChangePasswordSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    StaffCreateSerializer,
    StaffSerializer,
    UserProfileSerializer,
    UserSerializer,
)
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

TAG_AUTH = 'Auth'
TAG_STAFF = 'Staff'
TAG_CUSTOMERS = 'Customers'
TAG_ROOM_TYPES = 'Room Types'
TAG_ROOMS = 'Rooms'
TAG_AMENITIES = 'Amenities'
TAG_HEALTH = 'Health'
TAG_BOOKINGS = 'Bookings'
TAG_PAYMENTS = 'Payments'
TAG_INVOICES = 'Invoices'
TAG_SERVICES = 'Hotel Services'
TAG_HOUSEKEEPING = 'Housekeeping'
TAG_NOTIFICATIONS = 'Notifications'
TAG_ANALYTICS = 'Analytics'

PARAM_PAGE = OpenApiParameter(name='page', type=int, location=OpenApiParameter.QUERY, description='Trang (mặc định 1)')
PARAM_PAGE_SIZE = OpenApiParameter(
    name='page_size', type=int, location=OpenApiParameter.QUERY, description='Số bản ghi/trang (max 100)',
)
PARAM_SEARCH = OpenApiParameter(name='search', type=str, location=OpenApiParameter.QUERY, required=False)


class MessageSerializer(serializers.Serializer):
    message = serializers.CharField()


class PasswordForgotResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    token = serializers.CharField(required=False, help_text='Chỉ trả khi ?debug=1')


class AvatarResponseSerializer(serializers.Serializer):
    avatar = serializers.URLField()


class StaffUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(required=False)
    phone = serializers.CharField(required=False)
    department = serializers.CharField(required=False)
    hire_date = serializers.DateField(required=False)


class AvailabilityQuerySerializer(serializers.Serializer):
    check_in = serializers.DateField(help_text='Ngày nhận phòng (YYYY-MM-DD)')
    check_out = serializers.DateField(help_text='Ngày trả phòng (YYYY-MM-DD)')
    adults = serializers.IntegerField(default=1, required=False)
    children = serializers.IntegerField(default=0, required=False)
    room_type_id = serializers.UUIDField(required=False)


class AvailabilityRoomTypeSerializer(serializers.Serializer):
    room_type_id = serializers.UUIDField()
    name = serializers.CharField()
    max_occupancy = serializers.IntegerField()
    primary_image = serializers.CharField(allow_blank=True)
    available_count = serializers.IntegerField()
    price_per_night = serializers.CharField()
    total_price = serializers.CharField()


class AvailabilityResponseSerializer(serializers.Serializer):
    check_in = serializers.DateField()
    check_out = serializers.DateField()
    nights = serializers.IntegerField()
    room_types = AvailabilityRoomTypeSerializer(many=True)


AUTH_REGISTER = RegisterSerializer
AUTH_CHANGE_PASSWORD = ChangePasswordSerializer
AUTH_FORGOT = PasswordResetRequestSerializer
AUTH_RESET = PasswordResetConfirmSerializer
AUTH_ME_PATCH = UserProfileSerializer
