from rest_framework import serializers
from decimal import Decimal

from app.serializers.accounts import UserSerializer
from app.models import Booking, BookingRoom, BookingStatus, BookingStatusHistory


class BookingRoomSerializer(serializers.ModelSerializer):
    room_id = serializers.UUIDField(source='room.id', read_only=True)
    room_number = serializers.CharField(source='room.room_number', read_only=True)
    room_type_name = serializers.CharField(source='room_type.name', read_only=True)

    class Meta:
        model = BookingRoom
        fields = (
            'id', 'room_id', 'room_number', 'room_type_name',
            'price_per_night', 'nights', 'subtotal',
        )


class BookingListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    customer_email = serializers.CharField(source='customer.email', read_only=True)
    remaining_balance = serializers.SerializerMethodField()
    actual_total_amount = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = (
            'id', 'booking_code', 'status', 'customer_name', 'customer_email',
            'check_in_date', 'check_out_date', 'total_amount', 'actual_total_amount', 'paid_amount',
            'payment_status', 'remaining_balance', 'created_at',
        )

    def get_remaining_balance(self, obj):
        return max(self._get_actual_total(obj) - obj.paid_amount, 0)
    
    def get_actual_total_amount(self, obj):
        return self._get_actual_total(obj)
    
    @staticmethod
    def _get_actual_total(obj):
        # booking.total_amount đã chứa tiền phòng + tất cả dịch vụ CONFIRMED
        # Chỉ cộng thêm những dịch vụ PENDING chưa được xác nhận
        service_total = Decimal('0')
        for order in obj.service_orders.filter(status='pending'):
            service_total += order.total_amount
        return obj.total_amount + service_total

class BookingDetailSerializer(serializers.ModelSerializer):
    customer = UserSerializer(read_only=True)
    rooms = BookingRoomSerializer(source='booking_rooms', many=True, read_only=True)
    nights = serializers.SerializerMethodField()
    remaining_balance = serializers.SerializerMethodField()
    actual_total_amount = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = (
            'id', 'booking_code', 'status', 'customer', 'check_in_date', 'check_out_date',
            'adults', 'children', 'nights', 'rooms', 'total_amount', 'actual_total_amount', 'paid_amount',
            'payment_status', 'remaining_balance', 'special_request',
            'checked_in_at', 'checked_out_at', 'cancelled_at', 'cancel_reason', 'created_at',
        )

    def get_nights(self, obj):
        return (obj.check_out_date - obj.check_in_date).days

    def get_remaining_balance(self, obj):
        return max(self._get_actual_total(obj) - obj.paid_amount, 0)
    
    def get_actual_total_amount(self, obj):
        return self._get_actual_total(obj)
    
    @staticmethod
    def _get_actual_total(obj):
        # booking.total_amount đã chứa tiền phòng + tất cả dịch vụ CONFIRMED
        # Chỉ cộng thêm những dịch vụ PENDING chưa được xác nhận
        service_total = Decimal('0')
        for order in obj.service_orders.filter(status='pending'):
            service_total += order.total_amount
        return obj.total_amount + service_total


class BookingCreateSerializer(serializers.Serializer):
    check_in_date = serializers.DateField()
    check_out_date = serializers.DateField()
    adults = serializers.IntegerField(default=1, min_value=1)
    children = serializers.IntegerField(default=0, min_value=0)
    app_return_url = serializers.URLField(required=False, allow_blank=True, default='')
    payment_method = serializers.ChoiceField(
        choices=[('vnpay', 'VNPay'), ('counter', 'Thanh toán tại quầy')],
        default='vnpay',
        required=False,
    )
    rooms = serializers.ListField(
        child=serializers.DictField(),
        help_text='[{"room_type_id": "uuid", "quantity": 1}]',
    )
    special_request = serializers.CharField(required=False, allow_blank=True, default='')

class WalkInGuestSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
    national_id = serializers.CharField(max_length=50)
    phone = serializers.CharField(required=False, allow_blank=True, default='')
    email = serializers.EmailField(required=False, allow_blank=True, default='')
    address = serializers.CharField(required=False, allow_blank=True, default='')
    notes = serializers.CharField(required=False, allow_blank=True, default='')


class BookingWalkInSerializer(serializers.Serializer):
    customer_id = serializers.UUIDField(required=False, allow_null=True)
    guest = WalkInGuestSerializer(required=False)
    check_in_date = serializers.DateField()
    check_out_date = serializers.DateField()
    adults = serializers.IntegerField(default=1, min_value=1)
    children = serializers.IntegerField(default=0, min_value=0)
    room_ids = serializers.ListField(child=serializers.UUIDField())
    special_request = serializers.CharField(required=False, allow_blank=True, default='')
    status = serializers.ChoiceField(
        choices=[BookingStatus.CONFIRMED, BookingStatus.PENDING],
        required=False,
    )

    def validate(self, data):
        customer_id = data.get('customer_id')
        guest = data.get('guest')
        if customer_id and guest:
            raise serializers.ValidationError('Chỉ dùng customer_id hoặc thông tin khách walk-in')
        if not customer_id and not guest:
            raise serializers.ValidationError('Cần customer_id hoặc thông tin khách walk-in')
        return data


class BookingCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default='')


class BookingActionNoteSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default='')


class BookingCheckInSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default='')


class BookingStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source='changed_by.full_name', read_only=True, default='')

    class Meta:
        model = BookingStatusHistory
        fields = ('from_status', 'to_status', 'changed_by_name', 'changed_at', 'note')



