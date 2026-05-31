from rest_framework import serializers

from app.models import Amenity, Room, RoomPrice, RoomType, RoomTypeImage


class AmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenity
        fields = ('id', 'name', 'icon', 'is_active')


class RoomTypeImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = RoomTypeImage
        fields = ('id', 'image', 'is_primary', 'sort_order')

    def get_image(self, obj):
        if not obj.image:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url


class RoomPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomPrice
        fields = ('id', 'price', 'valid_from', 'valid_to', 'is_active')


class RoomTypeListSerializer(serializers.ModelSerializer):
    primary_image = serializers.SerializerMethodField()
    amenities = AmenitySerializer(many=True, read_only=True)

    class Meta:
        model = RoomType
        fields = (
            'id', 'name', 'description', 'max_occupancy', 'base_price',
            'primary_image', 'amenities', 'is_active',
        )

    def get_primary_image(self, obj):
        img = obj.images.filter(is_primary=True, is_active=True).first()
        if not img:
            img = obj.images.filter(is_active=True).order_by('sort_order').first()
        if img and img.image:
            request = self.context.get('request')
            url = img.image.url
            return request.build_absolute_uri(url) if request else url
        return None


class RoomTypeDetailSerializer(RoomTypeListSerializer):
    images = RoomTypeImageSerializer(many=True, read_only=True)
    prices = RoomPriceSerializer(many=True, read_only=True)

    class Meta(RoomTypeListSerializer.Meta):
        fields = RoomTypeListSerializer.Meta.fields + ('images', 'prices', 'created_at', 'updated_at')


class RoomListSerializer(serializers.ModelSerializer):
    room_type = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = (
            'id', 'room_number', 'floor', 'room_type', 'status', 'notes', 'is_active',
        )

    def get_room_type(self, obj):
        return {'id': str(obj.room_type_id), 'name': obj.room_type.name}


class RoomDetailSerializer(RoomListSerializer):
    class Meta(RoomListSerializer.Meta):
        fields = RoomListSerializer.Meta.fields + ('created_at', 'updated_at')


from rest_framework import serializers

from app.models import Amenity, Room, RoomPrice, RoomStatus, RoomType, RoomTypeImage


class RoomTypeWriteSerializer(serializers.ModelSerializer):
    amenity_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True,
    )

    class Meta:
        model = RoomType
        fields = (
            'name', 'description', 'max_occupancy', 'base_price', 'amenity_ids', 'is_active',
        )

    def create(self, validated_data):
        amenity_ids = validated_data.pop('amenity_ids', [])
        instance = super().create(validated_data)
        if amenity_ids:
            instance.amenities.set(Amenity.objects.filter(pk__in=amenity_ids))
        return instance

    def update(self, instance, validated_data):
        amenity_ids = validated_data.pop('amenity_ids', None)
        instance = super().update(instance, validated_data)
        if amenity_ids is not None:
            instance.amenities.set(Amenity.objects.filter(pk__in=amenity_ids))
        return instance


class RoomWriteSerializer(serializers.ModelSerializer):
    room_type_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Room
        fields = ('room_number', 'floor', 'room_type_id', 'status', 'notes', 'is_active')

    def validate_room_type_id(self, value):
        if not RoomType.objects.filter(pk=value, is_active=True).exists():
            raise serializers.ValidationError('Room type không tồn tại')
        return value

    def create(self, validated_data):
        room_type_id = validated_data.pop('room_type_id')
        return Room.objects.create(room_type_id=room_type_id, **validated_data)

    def update(self, instance, validated_data):
        room_type_id = validated_data.pop('room_type_id', None)
        if room_type_id is not None:
            instance.room_type_id = room_type_id
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class RoomStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=RoomStatus.choices)
    notes = serializers.CharField(required=False, allow_blank=True)


class AmenityWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenity
        fields = ('name', 'icon', 'is_active')


class RoomTypeImageWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomTypeImage
        fields = ('image', 'is_primary', 'sort_order')


class RoomPriceWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomPrice
        fields = ('price', 'valid_from', 'valid_to', 'is_active')

