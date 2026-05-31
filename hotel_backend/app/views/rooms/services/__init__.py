from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Q

from app.core.exceptions import BusinessException
from app.models import Room, RoomPrice, RoomStatus, RoomType


class RoomService:
    @staticmethod
    def update_room_status(room, new_status, notes=None, user=None):
        allowed_transitions = {
            RoomStatus.AVAILABLE: {RoomStatus.RESERVED, RoomStatus.MAINTENANCE, RoomStatus.CLEANING},
            RoomStatus.RESERVED: {RoomStatus.AVAILABLE, RoomStatus.OCCUPIED, RoomStatus.MAINTENANCE},
            RoomStatus.OCCUPIED: {RoomStatus.CLEANING, RoomStatus.MAINTENANCE},
            RoomStatus.CLEANING: {RoomStatus.AVAILABLE, RoomStatus.MAINTENANCE},
            RoomStatus.MAINTENANCE: {RoomStatus.AVAILABLE, RoomStatus.CLEANING},
        }
        if user and user.role == 'housekeeping' and not user.is_superuser:
            if not (room.status == RoomStatus.CLEANING and new_status == RoomStatus.AVAILABLE):
                raise BusinessException(
                    'Housekeeping chỉ được chuyển cleaning → available',
                    code='FORBIDDEN_TRANSITION',
                    status_code=403,
                )
        elif new_status not in allowed_transitions.get(room.status, set()):
            raise BusinessException(
                f'Không thể chuyển từ {room.status} sang {new_status}',
                code='INVALID_STATUS_TRANSITION',
            )
        room.status = new_status
        if notes is not None:
            room.notes = notes
        room.save(update_fields=['status', 'notes', 'updated_at'])
        return room

    @staticmethod
    def get_price_for_date(room_type, target_date):
        price = RoomPrice.objects.filter(
            room_type=room_type,
            is_active=True,
            valid_from__lte=target_date,
        ).filter(
            Q(valid_to__isnull=True) | Q(valid_to__gte=target_date),
        ).order_by('-valid_from').first()
        if price:
            return price.price
        return room_type.base_price

    @staticmethod
    def check_availability(check_in, check_out, adults=1, children=0, room_type_id=None):
        if check_out <= check_in:
            raise BusinessException('check_out phải sau check_in', code='INVALID_DATE_RANGE')
        nights = (check_out - check_in).days
        room_types = RoomType.objects.filter(is_active=True).prefetch_related('images')
        if room_type_id:
            room_types = room_types.filter(pk=room_type_id)
        busy_room_ids = RoomService._busy_room_ids(check_in, check_out)
        results = []
        for rt in room_types:
            if adults + children > rt.max_occupancy:
                continue
            available_count = Room.objects.filter(
                room_type=rt,
                is_active=True,
                status__in=[RoomStatus.AVAILABLE, RoomStatus.RESERVED, RoomStatus.CLEANING],
            ).exclude(pk__in=busy_room_ids).count()
            if available_count == 0:
                continue
            price_per_night = RoomService.get_price_for_date(rt, check_in)
            primary = next((img for img in rt.images.all() if img.is_active and img.is_primary), None)
            if not primary:
                primary = next((img for img in rt.images.all() if img.is_active), None)
            results.append({
                'room_type_id': str(rt.id),
                'name': rt.name,
                'max_occupancy': rt.max_occupancy,
                'primary_image': primary.image.url if primary and primary.image else '',
                'available_count': available_count,
                'price_per_night': str(price_per_night),
                'total_price': str(price_per_night * nights),
            })
        return {
            'check_in': check_in.isoformat(),
            'check_out': check_out.isoformat(),
            'nights': nights,
            'room_types': results,
        }

    @staticmethod
    def _busy_room_ids(check_in, check_out):
        from app.models import BookingRoom
        active_statuses = ['confirmed', 'checked_in', 'pending']
        return BookingRoom.objects.filter(
            booking__status__in=active_statuses,
            booking__check_in_date__lt=check_out,
            booking__check_out_date__gt=check_in,
            booking__is_active=True,
        ).values_list('room_id', flat=True)

