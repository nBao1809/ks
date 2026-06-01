from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate, TruncMonth
from django.conf import settings

from app.models import Booking, BookingStatus
from app.models import Payment, PaymentStatus
from app.models import Room
from app.models import ServiceOrder, ServiceOrderItem


class ReportService:
    @staticmethod
    def revenue(period, year, month=None, quarter=None, target_date=None):
        payments = Payment.objects.filter(status=PaymentStatus.COMPLETED, is_active=True)
        if period == 'day':
            day = target_date or date.today()
            payments = payments.filter(paid_at__date=day)
        elif period == 'year':
            payments = payments.filter(paid_at__year=year)
        elif period == 'month' and month:
            payments = payments.filter(paid_at__year=year, paid_at__month=month)
        elif period == 'quarter' and quarter:
            start_month = (quarter - 1) * 3 + 1
            end_month = start_month + 2
            payments = payments.filter(paid_at__year=year, paid_at__month__gte=start_month, paid_at__month__lte=end_month)

        total = payments.aggregate(t=Sum('amount'))['t'] or Decimal('0')
        room_rev = payments.filter(booking__isnull=False).aggregate(t=Sum('amount'))['t'] or Decimal('0')
        by_method = {}
        for row in payments.values('method').annotate(total=Sum('amount')):
            by_method[row['method']] = str(row['total'] or 0)

        daily = []
        if period == 'month' and month:
            for row in payments.annotate(d=TruncDate('paid_at')).values('d').annotate(total=Sum('amount')).order_by('d'):
                if row['d']:
                    daily.append({'date': row['d'].isoformat(), 'revenue': str(row['total'] or 0)})
        elif period == 'quarter' and quarter:
            start_month = (quarter - 1) * 3 + 1
            for m in range(start_month, start_month + 3):
                month_total = payments.filter(paid_at__month=m).aggregate(t=Sum('amount'))['t'] or Decimal('0')
                daily.append({'date': f'{year}-{m:02d}', 'revenue': str(month_total)})
        elif period == 'year':
            for m in range(1, 13):
                month_total = payments.filter(paid_at__month=m).aggregate(t=Sum('amount'))['t'] or Decimal('0')
                daily.append({'date': f'{year}-{m:02d}', 'revenue': str(month_total)})

        return {
            'period': period,
            'year': year,
            'month': month,
            'quarter': quarter,
            'date': target_date.isoformat() if target_date else None,
            'total_revenue': str(total),
            'room_revenue': str(room_rev),
            'service_revenue': '0',
            'payment_breakdown': by_method,
            'daily': daily,
        }

    @staticmethod
    def occupancy(date_from, date_to):
        total_rooms = Room.objects.filter(is_active=True).count()
        days = (date_to - date_from).days or 1
        available_nights = total_rooms * days
        bookings = Booking.objects.filter(
            is_active=True,
            status__in=(BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT),
            check_in_date__lt=date_to,
            check_out_date__gt=date_from,
        )
        occupied = 0
        for b in bookings:
            overlap_start = max(b.check_in_date, date_from)
            overlap_end = min(b.check_out_date, date_to)
            nights = max(0, (overlap_end - overlap_start).days)
            occupied += nights * b.booking_rooms.count()

        rate = occupied / available_nights if available_nights else 0
        return {
            'date_from': date_from.isoformat(),
            'date_to': date_to.isoformat(),
            'total_rooms': total_rooms,
            'occupancy_rate': round(rate, 4),
            'occupied_room_nights': occupied,
            'available_room_nights': available_nights,
        }

    @staticmethod
    def booking_stats(period, year, quarter=None):
        qs = Booking.objects.filter(is_active=True, created_at__year=year)
        if period == 'quarter' and quarter:
            start_m = (quarter - 1) * 3 + 1
            end_m = start_m + 2
            qs = qs.filter(created_at__month__gte=start_m, created_at__month__lte=end_m)
        total = qs.count()
        by_status = {row['status']: row['c'] for row in qs.values('status').annotate(c=Count('id'))}
        cancelled = by_status.get(BookingStatus.CANCELLED, 0)
        return {
            'total_bookings': total,
            'by_status': by_status,
            'cancellation_rate': round(cancelled / total, 4) if total else 0,
        }

    @staticmethod
    def service_stats(period, year, month=None):
        items = ServiceOrderItem.objects.filter(
            order__is_active=True,
            order__created_at__year=year,
        )
        if period == 'month' and month:
            items = items.filter(order__created_at__month=month)
        top = []
        for row in items.values('service__name').annotate(
            order_count=Count('id'),
            revenue=Sum('subtotal'),
        ).order_by('-revenue')[:10]:
            top.append({
                'service_name': row['service__name'] or 'Dịch vụ khác',
                'order_count': row['order_count'],
                'revenue': str(row['revenue'] or 0),
            })
        total = items.aggregate(t=Sum('subtotal'))['t'] or Decimal('0')
        return {'top_services': top, 'total_service_revenue': str(total)}

    @staticmethod
    def dashboard(target_date=None):
        target = target_date or date.today()

        hotel_tz_name = getattr(settings, 'HOTEL_TIME_ZONE', 'Asia/Ho_Chi_Minh')
        hotel_tz = ZoneInfo(hotel_tz_name)
        day_start = datetime.combine(target, time.min, tzinfo=hotel_tz)
        day_end = day_start + timedelta(days=1)

        return {
            # Count real operations in hotel local day, not UTC date truncation.
            'today_check_ins': Booking.objects.filter(
                is_active=True,
                checked_in_at__gte=day_start,
                checked_in_at__lt=day_end,
            ).count(),
            'today_check_outs': Booking.objects.filter(
                is_active=True,
                checked_out_at__gte=day_start,
                checked_out_at__lt=day_end,
            ).count(),
            'rooms_available': Room.objects.filter(status='available', is_active=True).count(),
            'rooms_occupied': Room.objects.filter(status='occupied', is_active=True).count(),
            'rooms_cleaning': Room.objects.filter(status='cleaning', is_active=True).count(),
            'pending_bookings': Booking.objects.filter(is_active=True, status=BookingStatus.PENDING).count(),
            'today_revenue': str(
                Payment.objects.filter(
                    is_active=True,
                    paid_at__gte=day_start,
                    paid_at__lt=day_end,
                    status=PaymentStatus.COMPLETED,
                ).aggregate(
                    t=Sum('amount'),
                )['t'] or 0,
            ),
            'pending_housekeeping_tasks': HousekeepingTask.objects.filter(
                status=TaskStatus.PENDING, is_active=True,
            ).count(),
        }

