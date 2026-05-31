from rest_framework import serializers

from app.models import Service, ServiceCategory, ServiceOrder, ServiceOrderItem


class ServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = ('id', 'name', 'slug', 'is_active')


class ServiceCategoryWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = ('name',)

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Tên danh mục không được để trống')
        return value

    def create(self, validated_data):
        from django.utils.text import slugify

        name = validated_data['name']
        base_slug = slugify(name) or 'danh-muc'
        slug = base_slug
        n = 1
        while ServiceCategory.objects.filter(slug=slug).exists():
            slug = f'{base_slug}-{n}'
            n += 1
        return ServiceCategory.objects.create(name=name, slug=slug)


class ServiceSerializer(serializers.ModelSerializer):
    category = ServiceCategorySerializer(read_only=True)
    category_id = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = Service
        fields = (
            'id', 'category', 'category_id', 'name', 'description', 'price', 'unit',
            'is_staff_only', 'is_active',
        )


class ServiceWriteSerializer(serializers.ModelSerializer):
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=ServiceCategory.objects.filter(is_active=True),
        source='category',
    )

    class Meta:
        model = Service
        fields = ('category_id', 'name', 'description', 'price', 'unit', 'is_staff_only', 'is_active')

    def validate_category_id(self, category):
        if not category.is_active:
            raise serializers.ValidationError('Danh mục không hợp lệ')
        return category


class ServiceOrderItemSerializer(serializers.ModelSerializer):
    service_name = serializers.SerializerMethodField()

    class Meta:
        model = ServiceOrderItem
        fields = ('id', 'service_name', 'description', 'quantity', 'unit_price', 'subtotal')

    def get_service_name(self, obj):
        if obj.service_id:
            return obj.service.name
        return obj.description


class ServiceOrderSerializer(serializers.ModelSerializer):
    items = ServiceOrderItemSerializer(many=True, read_only=True)
    booking_code = serializers.CharField(source='booking.booking_code', read_only=True)

    class Meta:
        model = ServiceOrder
        fields = (
            'id', 'booking_id', 'booking_code', 'status', 'total_amount',
            'scheduled_at', 'note', 'items', 'created_at',
        )


class ServiceOrderItemInputSerializer(serializers.Serializer):
    service_id = serializers.UUIDField(required=False, allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    unit_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True,
    )
    quantity = serializers.IntegerField(min_value=1, default=1)


    def validate(self, data):
        if data.get('service_id'):
            return data
        if (data.get('description') or '').strip() and data.get('unit_price') is not None:
            return data
        raise serializers.ValidationError(
            'Mỗi dòng cần service_id hoặc description + unit_price (nhập thủ công)',
        )


class ServiceOrderCreateSerializer(serializers.Serializer):
    booking_id = serializers.UUIDField()
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True)
    note = serializers.CharField(required=False, allow_blank=True, default='')
    items = ServiceOrderItemInputSerializer(many=True)

