from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from app.models import UserRole
from app.models import Booking
from app.core.exceptions import BusinessException
from app.models import Service, ServiceOrder, ServiceOrderItem, ServiceOrderStatus


class ServiceOrderService:
    STAFF_ROLES = (UserRole.MANAGER, UserRole.RECEPTIONIST)

    @staticmethod
    def _is_staff(user):
        return user.is_superuser or user.role in ServiceOrderService.STAFF_ROLES

    @staticmethod
    def _resolve_item(user, item):
        service_id = item.get('service_id')
        if service_id:
            service = Service.objects.filter(pk=service_id, is_active=True).first()
            if not service:
                raise BusinessException('Dịch vụ không tồn tại', code='NOT_FOUND', status_code=404)
            if service.is_staff_only and not ServiceOrderService._is_staff(user):
                raise BusinessException('Không có quyền', code='FORBIDDEN', status_code=403)
            qty = item.get('quantity', 1)
            unit_price = service.price
            subtotal = unit_price * qty
            return {
                'service': service,
                'description': '',
                'quantity': qty,
                'unit_price': unit_price,
                'subtotal': subtotal,
            }

        if not ServiceOrderService._is_staff(user):
            raise BusinessException('Chỉ nhân viên được nhập dịch vụ thủ công', code='FORBIDDEN', status_code=403)

        description = (item.get('description') or '').strip()
        unit_price = item.get('unit_price')
        if not description or unit_price is None:
            raise BusinessException(
                'Dòng tùy chỉnh cần description và unit_price',
                code='VALIDATION_ERROR',
            )
        qty = item.get('quantity', 1)
        unit_price = Decimal(str(unit_price))
        if unit_price < 0:
            raise BusinessException('Đơn giá không hợp lệ', code='VALIDATION_ERROR')
        subtotal = unit_price * qty
        return {
            'service': None,
            'description': description,
            'quantity': qty,
            'unit_price': unit_price,
            'subtotal': subtotal,
        }

    @staticmethod
    @transaction.atomic
    def create_order(user, booking_id, items_data, scheduled_at=None, note=''):
        booking = Booking.objects.filter(pk=booking_id, is_active=True).first()
        if not booking:
            raise BusinessException('Booking không tồn tại', code='NOT_FOUND', status_code=404)
        if user.role == UserRole.CUSTOMER and booking.customer_id != user.id:
            raise BusinessException('Không có quyền', code='FORBIDDEN', status_code=403)
        if not items_data:
            raise BusinessException('Cần ít nhất một dịch vụ', code='VALIDATION_ERROR')

        order = ServiceOrder.objects.create(
            booking=booking,
            customer=booking.customer,
            scheduled_at=scheduled_at,
            note=note or '',
            status=ServiceOrderStatus.CONFIRMED
            if ServiceOrderService._is_staff(user)
            else ServiceOrderStatus.PENDING,
        )
        total = Decimal('0')
        for item in items_data:
            resolved = ServiceOrderService._resolve_item(user, item)
            ServiceOrderItem.objects.create(
                order=order,
                service=resolved['service'],
                description=resolved['description'],
                quantity=resolved['quantity'],
                unit_price=resolved['unit_price'],
                subtotal=resolved['subtotal'],
            )
            total += resolved['subtotal']
        order.total_amount = total
        order.save(update_fields=['total_amount', 'updated_at'])
        
        # Cộng tiền vào booking nếu được tạo với status CONFIRMED (staff tạo trực tiếp)
        # Set confirmed_at để tracking
        if order.status == ServiceOrderStatus.CONFIRMED:
            order.confirmed_at = timezone.now()
            order.save(update_fields=['confirmed_at'])
        
        # Tính lại tổng tiền booking từ tất cả dịch vụ CONFIRMED
        from app.views.bookings.services.booking_service import BookingService
        BookingService.recalculate_total_amount(booking)
        
        from app.views.payments.services.payment_service import PaymentService
        PaymentService.sync_booking_payment(booking)
        return order

    @staticmethod
    @transaction.atomic
    def confirm(order_id, user):
        order = ServiceOrder.objects.filter(pk=order_id).first()
        if not order:
            raise BusinessException('Đơn không tồn tại', code='NOT_FOUND', status_code=404)
        if order.status != ServiceOrderStatus.PENDING:
            raise BusinessException('Trạng thái không hợp lệ', code='INVALID_STATUS')
        order.status = ServiceOrderStatus.CONFIRMED
        order.confirmed_at = timezone.now()
        order.save(update_fields=['status', 'confirmed_at', 'updated_at'])
        
        # Tính lại tổng tiền booking từ tất cả dịch vụ CONFIRMED
        booking = order.booking
        from app.views.bookings.services.booking_service import BookingService
        BookingService.recalculate_total_amount(booking)
        
        # Nếu booking đã được thanh toán, regenerate invoice và gửi email cập nhật
        from app.models import BookingPaymentStatus
        if booking.payment_status == BookingPaymentStatus.PAID:
            try:
                from app.views.payments.services.payment_service import PaymentService
                invoice, _ = PaymentService._ensure_invoice(booking)
                transaction.on_commit(lambda invoice_id=invoice.id: PaymentService._send_invoice_email(invoice_id))
            except Exception:
                pass
        
        try:
            from app.views.notifications.services.notification_service import NotificationService
            NotificationService.service_order_confirmed(order)
        except Exception:
            pass
        return order

    @staticmethod
    @transaction.atomic
    def cancel(order_id, user):
        order = ServiceOrder.objects.filter(pk=order_id).first()
        if not order:
            raise BusinessException('Đơn không tồn tại', code='NOT_FOUND', status_code=404)
        if order.status in (ServiceOrderStatus.COMPLETED, ServiceOrderStatus.CANCELLED):
            raise BusinessException('Không thể hủy', code='INVALID_STATUS')
        if user.role == UserRole.CUSTOMER and order.status != ServiceOrderStatus.PENDING:
            raise BusinessException('Chỉ hủy được đơn pending', code='FORBIDDEN', status_code=403)
        was_confirmed = order.status == ServiceOrderStatus.CONFIRMED
        order.status = ServiceOrderStatus.CANCELLED
        order.save(update_fields=['status', 'updated_at'])
        
        # Tính lại tổng tiền booking nếu đơn đã được confirm trước đó
        if was_confirmed:
            booking = order.booking
            from app.views.bookings.services.booking_service import BookingService
            BookingService.recalculate_total_amount(booking)
        return order

    @staticmethod
    def queryset_for_user(user):
        qs = ServiceOrder.objects.select_related('booking', 'customer').prefetch_related('items__service')
        if user.is_superuser:
            return qs.filter(is_active=True)
        if user.role == UserRole.CUSTOMER:
            return qs.filter(customer_id=user.id, is_active=True)
        if user.role in ServiceOrderService.STAFF_ROLES:
            return qs.filter(is_active=True)
        return qs.none()

