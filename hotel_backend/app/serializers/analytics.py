from rest_framework import serializers


class RevenueReportSerializer(serializers.Serializer):
    period = serializers.CharField()
    year = serializers.IntegerField()
    month = serializers.IntegerField(allow_null=True)
    quarter = serializers.IntegerField(allow_null=True)
    total_revenue = serializers.CharField()
    room_revenue = serializers.CharField()
    service_revenue = serializers.CharField()
    payment_breakdown = serializers.DictField()
    daily = serializers.ListField(child=serializers.DictField())


class OccupancyReportSerializer(serializers.Serializer):
    date_from = serializers.CharField()
    date_to = serializers.CharField()
    total_rooms = serializers.IntegerField()
    occupancy_rate = serializers.FloatField()
    occupied_room_nights = serializers.IntegerField()
    available_room_nights = serializers.IntegerField()


class BookingStatsSerializer(serializers.Serializer):
    total_bookings = serializers.IntegerField()
    by_status = serializers.DictField()
    cancellation_rate = serializers.FloatField()


class ServiceStatsSerializer(serializers.Serializer):
    top_services = serializers.ListField(child=serializers.DictField())
    total_service_revenue = serializers.CharField()


class DashboardSerializer(serializers.Serializer):
    today_check_ins = serializers.IntegerField()
    today_check_outs = serializers.IntegerField()
    rooms_available = serializers.IntegerField()
    rooms_occupied = serializers.IntegerField()
    rooms_cleaning = serializers.IntegerField()
    pending_bookings = serializers.IntegerField()
    today_revenue = serializers.CharField()
    pending_housekeeping_tasks = serializers.IntegerField()


class NotificationReadAllSerializer(serializers.Serializer):
    updated = serializers.IntegerField()
