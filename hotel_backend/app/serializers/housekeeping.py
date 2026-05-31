from rest_framework import serializers

from app.models import HousekeepingLog, HousekeepingTask, TaskPriority, TaskStatus, TaskType


class HousekeepingUserSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    full_name = serializers.CharField()


class HousekeepingRoomSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    room_number = serializers.CharField()
    floor = serializers.IntegerField()
    status = serializers.CharField()


class HousekeepingTaskSerializer(serializers.ModelSerializer):
    room = serializers.SerializerMethodField()
    assigned_to = serializers.SerializerMethodField()

    class Meta:
        model = HousekeepingTask
        fields = (
            'id', 'room', 'assigned_to', 'status', 'priority', 'task_type',
            'notes', 'started_at', 'completed_at', 'created_at',
        )

    def get_room(self, obj):
        return {
            'id': str(obj.room_id),
            'room_number': obj.room.room_number,
            'floor': obj.room.floor,
            'status': obj.room.status,
        }

    def get_assigned_to(self, obj):
        if not obj.assigned_to:
            return None
        return {'id': str(obj.assigned_to_id), 'full_name': obj.assigned_to.full_name}


class HousekeepingTaskCreateSerializer(serializers.Serializer):
    room_id = serializers.UUIDField()
    assigned_to_id = serializers.UUIDField(required=False, allow_null=True)
    priority = serializers.ChoiceField(choices=TaskPriority.choices, default=TaskPriority.NORMAL)
    task_type = serializers.ChoiceField(choices=TaskType.choices, default=TaskType.DAILY_CLEAN)
    notes = serializers.CharField(required=False, allow_blank=True, default='')


class HousekeepingTaskAssignSerializer(serializers.Serializer):
    assigned_to_id = serializers.UUIDField()


class HousekeepingTaskUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=TaskStatus.choices)
    notes = serializers.CharField(required=False, allow_blank=True)


class HousekeepingLogSerializer(serializers.ModelSerializer):
    performed_by_name = serializers.CharField(source='performed_by.full_name', read_only=True, default='')

    class Meta:
        model = HousekeepingLog
        fields = ('action', 'performed_by_name', 'timestamp', 'note')

