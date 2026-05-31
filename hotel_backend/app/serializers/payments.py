from rest_framework import serializers

from app.models import Invoice, Payment, PaymentMethod, Transaction


class PaymentSerializer(serializers.ModelSerializer):
    booking_code = serializers.CharField(source='booking.booking_code', read_only=True)

    class Meta:
        model = Payment
        fields = (
            'id', 'booking_id', 'booking_code', 'amount', 'method', 'status',
            'transaction_ref', 'vnp_transaction_no', 'paid_at', 'payment_url',
            'gateway_meta', 'created_at',
        )


class PaymentCreateSerializer(serializers.Serializer):
    booking_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    method = serializers.ChoiceField(choices=PaymentMethod.choices)
    bank_code = serializers.CharField(required=False, allow_blank=True, default='')
    locale = serializers.ChoiceField(choices=[('vn', 'vn'), ('en', 'en')], default='vn', required=False)


class VNPayReturnSerializer(serializers.Serializer):
    payment = PaymentSerializer()
    vnp_response_code = serializers.CharField()
    vnp_transaction_status = serializers.CharField(allow_blank=True)
    vnp_transaction_no = serializers.CharField(allow_blank=True)
    success = serializers.BooleanField()


class PaymentRefundSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    reason = serializers.CharField(required=False, allow_blank=True, default='')


class PaymentWebhookSerializer(serializers.Serializer):
    transaction_ref = serializers.CharField()
    status = serializers.CharField(required=False)


class InvoiceLineItemSerializer(serializers.Serializer):
    description = serializers.CharField()
    amount = serializers.CharField()


class InvoiceSerializer(serializers.ModelSerializer):
    booking_code = serializers.CharField(source='booking.booking_code', read_only=True)
    line_items = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = (
            'id', 'invoice_number', 'booking_id', 'booking_code',
            'subtotal', 'tax', 'discount', 'total', 'issued_at', 'pdf_url', 'line_items',
        )

    def get_line_items(self, obj):
        items = []
        for br in obj.booking.booking_rooms.all():
            items.append({
                'description': f'{br.room_type.name} - {br.room.room_number} x {br.nights} đêm',
                'amount': str(br.subtotal),
            })
        return items


class InvoiceCreateSerializer(serializers.Serializer):
    booking_id = serializers.UUIDField()

