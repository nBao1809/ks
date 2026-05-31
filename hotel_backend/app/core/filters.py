import django_filters

from app.models import Room, RoomType


class RoomFilter(django_filters.FilterSet):
    status = django_filters.CharFilter()
    floor = django_filters.NumberFilter()
    room_type_id = django_filters.UUIDFilter(field_name='room_type_id')

    class Meta:
        model = Room
        fields = ['status', 'floor', 'room_type_id']


class RoomTypeFilter(django_filters.FilterSet):
    is_active = django_filters.BooleanFilter()

    class Meta:
        model = RoomType
        fields = ['is_active']
