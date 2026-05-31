from rest_framework import serializers

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


