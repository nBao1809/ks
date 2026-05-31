from app.models import Notification, NotificationChannel, NotificationType


class NotificationService:
    @staticmethod
    def send(user, notification_type, title, body, metadata=None, channel=NotificationChannel.IN_APP):
        return Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            body=body,
            channel=channel,
            metadata=metadata or {},
        )

    @staticmethod
    def booking_confirmed(booking):
        return NotificationService.send(
            booking.customer,
            NotificationType.BOOKING_CONFIRMED,
            'Đặt phòng thành công',
            f'Booking {booking.booking_code} đã được xác nhận',
            {'booking_id': str(booking.id)},
        )

    @staticmethod
    def payment_received(payment):
        return NotificationService.send(
            payment.booking.customer,
            NotificationType.PAYMENT_RECEIVED,
            'Thanh toán thành công',
            f'Đã thanh toán {payment.amount} cho {payment.booking.booking_code}',
            {'payment_id': str(payment.id)},
        )

    @staticmethod
    def _service_items_summary(order, max_items=3):
        items = list(order.items.select_related('service').all())
        if not items:
            return 'đơn dịch vụ của bạn'

        labels = [f'{item.service.name} x{item.quantity}' for item in items]
        if len(labels) > max_items:
            shown = ', '.join(labels[:max_items])
            return f'{shown} và {len(labels) - max_items} dịch vụ khác'
        return ', '.join(labels)

    @staticmethod
    def service_order_confirmed(order):
        services_text = NotificationService._service_items_summary(order)
        return NotificationService.send(
            order.customer,
            NotificationType.SERVICE_ORDER_CONFIRMED,
            'Dịch vụ đã được xác nhận',
            f'{services_text} đã được xác nhận cho booking {order.booking.booking_code}',
            {'service_order_id': str(order.id), 'booking_id': str(order.booking_id)},
        )

    @staticmethod
    def room_ready(user, room):
        return NotificationService.send(
            user,
            NotificationType.ROOM_READY,
            'Phòng sẵn sàng',
            f'Phòng {room.room_number} đã dọn xong',
            {'room_id': str(room.id)},
        )

