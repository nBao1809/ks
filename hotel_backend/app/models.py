import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

from app.core.utils import get_current_user


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_created',
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.created_by_id:
            user = get_current_user()
            if user and user.is_authenticated:
                self.created_by = user
        super().save(*args, **kwargs)


class UserRole:
    MANAGER = 'manager'
    RECEPTIONIST = 'receptionist'
    HOUSEKEEPING = 'housekeeping'
    CUSTOMER = 'customer'

    CHOICES = [
        (MANAGER, 'Manager'),
        (RECEPTIONIST, 'Receptionist'),
        (HOUSEKEEPING, 'Housekeeping'),
        (CUSTOMER, 'Customer'),
    ]

    STAFF = (MANAGER, RECEPTIONIST, HOUSEKEEPING)


class BookingStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    CONFIRMED = 'confirmed', 'Confirmed'
    CHECKED_IN = 'checked_in', 'Checked In'
    CHECKED_OUT = 'checked_out', 'Checked Out'
    CANCELLED = 'cancelled', 'Cancelled'


class BookingPaymentStatus(models.TextChoices):
    UNPAID = 'unpaid', 'Unpaid'
    PARTIAL = 'partial', 'Partial'
    PAID = 'paid', 'Paid'


class RoomStatus(models.TextChoices):
    AVAILABLE = 'available', 'Available'
    RESERVED = 'reserved', 'Reserved'
    OCCUPIED = 'occupied', 'Occupied'
    CLEANING = 'cleaning', 'Cleaning'
    MAINTENANCE = 'maintenance', 'Maintenance'


class PaymentMethod(models.TextChoices):
    CASH = 'cash', 'Cash'
    CARD = 'card', 'Card'
    BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
    MOMO = 'momo', 'MoMo'
    VNPAY = 'vnpay', 'VNPay'


class PaymentStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'
    REFUNDED = 'refunded', 'Refunded'


class ServiceOrderStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    CONFIRMED = 'confirmed', 'Confirmed'
    COMPLETED = 'completed', 'Completed'
    CANCELLED = 'cancelled', 'Cancelled'


class TaskStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    IN_PROGRESS = 'in_progress', 'In Progress'
    COMPLETED = 'completed', 'Completed'
    CANCELLED = 'cancelled', 'Cancelled'


class TaskPriority(models.TextChoices):
    LOW = 'low', 'Low'
    NORMAL = 'normal', 'Normal'
    HIGH = 'high', 'High'


class TaskType(models.TextChoices):
    CHECKOUT_CLEAN = 'checkout_clean', 'Checkout Clean'
    DAILY_CLEAN = 'daily_clean', 'Daily Clean'
    MAINTENANCE = 'maintenance', 'Maintenance'


class NotificationType(models.TextChoices):
    BOOKING_CONFIRMED = 'booking_confirmed', 'Booking Confirmed'
    PAYMENT_RECEIVED = 'payment_received', 'Payment Received'
    SERVICE_ORDER_CONFIRMED = 'service_order_confirmed', 'Service Order Confirmed'
    ROOM_READY = 'room_ready', 'Room Ready'
    PASSWORD_RESET = 'password_reset', 'Password Reset'


class NotificationChannel(models.TextChoices):
    EMAIL = 'email', 'Email'
    IN_APP = 'in_app', 'In App'
    PUSH = 'push', 'Push'


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=UserRole.CHOICES, default=UserRole.CUSTOMER)
    phone = models.CharField(max_length=20, blank=True, default='')
    full_name = models.CharField(max_length=255, blank=True, default='')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    email_verified = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'accounts_user'

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.email
        if not self.full_name and (self.first_name or self.last_name):
            self.full_name = f'{self.first_name} {self.last_name}'.strip()
        super().save(*args, **kwargs)


class StaffProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name='staff_profile')
    employee_code = models.CharField(max_length=50, unique=True)
    department = models.CharField(max_length=100, blank=True, default='')
    hire_date = models.DateField(null=True, blank=True)
    manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_staff',
    )

    class Meta:
        db_table = 'accounts_staff_profile'


class GuestProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='guest_profile',
    )
    national_id = models.CharField(max_length=50, blank=True, default='', db_index=True)
    address = models.TextField(blank=True, default='')
    notes = models.TextField(blank=True, default='')
    is_temporary = models.BooleanField(default=True)

    class Meta:
        db_table = 'accounts_guest_profile'


class PasswordResetToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reset_tokens')
    token_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'accounts_password_reset_token'


class Amenity(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, blank=True, default='')

    class Meta:
        db_table = 'rooms_amenity'
        ordering = ['name']

    def __str__(self):
        return self.name


class RoomType(BaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    max_occupancy = models.PositiveIntegerField(default=2)
    base_price = models.DecimalField(max_digits=12, decimal_places=2)
    amenities = models.ManyToManyField(Amenity, blank=True, related_name='room_types')

    class Meta:
        db_table = 'rooms_room_type'
        ordering = ['name']

    def __str__(self):
        return self.name


class RoomTypeImage(BaseModel):
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='room_types/')
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'rooms_room_type_image'
        ordering = ['sort_order', 'created_at']


class RoomPrice(BaseModel):
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE, related_name='prices')
    price = models.DecimalField(max_digits=12, decimal_places=2)
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'rooms_room_price'
        indexes = [
            models.Index(fields=['room_type', 'valid_from', 'valid_to']),
        ]


class Room(BaseModel):
    room_number = models.CharField(max_length=20, unique=True)
    floor = models.PositiveIntegerField(default=1)
    room_type = models.ForeignKey(RoomType, on_delete=models.PROTECT, related_name='rooms')
    status = models.CharField(max_length=20, choices=RoomStatus.choices, default=RoomStatus.AVAILABLE)
    notes = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'rooms_room'
        ordering = ['floor', 'room_number']
        indexes = [
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return self.room_number


class ServiceCategory(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)

    class Meta:
        db_table = 'hotel_service_category'
        verbose_name_plural = 'service categories'

    def __str__(self):
        return self.name


class Service(BaseModel):
    category = models.ForeignKey(ServiceCategory, on_delete=models.PROTECT, related_name='services')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    price = models.DecimalField(max_digits=12, decimal_places=2)
    unit = models.CharField(max_length=50, default='per_person')
    is_staff_only = models.BooleanField(
        default=False,
        help_text='Chỉ nhân viên thấy (tiền cọc, minibar, hư hỏng, …)',
    )

    class Meta:
        db_table = 'hotel_service'

    def __str__(self):
        return self.name


class Booking(BaseModel):
    booking_code = models.CharField(max_length=30, unique=True)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='bookings',
    )
    status = models.CharField(max_length=20, choices=BookingStatus.choices, default=BookingStatus.PENDING)
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    adults = models.PositiveIntegerField(default=1)
    children = models.PositiveIntegerField(default=0)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    payment_status = models.CharField(
        max_length=20,
        choices=BookingPaymentStatus.choices,
        default=BookingPaymentStatus.UNPAID,
    )
    special_request = models.TextField(blank=True, default='')
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_out_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'bookings_booking'
        indexes = [
            models.Index(fields=['check_in_date', 'check_out_date', 'status']),
        ]


class BookingRoom(BaseModel):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='booking_rooms')
    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name='booking_rooms')
    room_type = models.ForeignKey(RoomType, on_delete=models.PROTECT)
    price_per_night = models.DecimalField(max_digits=12, decimal_places=2)
    nights = models.PositiveIntegerField()
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        db_table = 'bookings_booking_room'
        unique_together = ('booking', 'room')


class BookingStatusHistory(models.Model):
    id = models.BigAutoField(primary_key=True)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='status_history')
    from_status = models.CharField(max_length=20, blank=True, default='')
    to_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    changed_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'bookings_status_history'
        ordering = ['-changed_at']


class ServiceOrder(BaseModel):
    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, related_name='service_orders')
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='service_orders')
    status = models.CharField(max_length=20, choices=ServiceOrderStatus.choices, default=ServiceOrderStatus.PENDING)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True, help_text='Thời điểm được confirm hoặc tạo với status CONFIRMED')
    note = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'hotel_service_order'


class ServiceOrderItem(BaseModel):
    order = models.ForeignKey(ServiceOrder, on_delete=models.CASCADE, related_name='items')
    service = models.ForeignKey(Service, on_delete=models.PROTECT, null=True, blank=True)
    description = models.CharField(max_length=255, blank=True, default='')
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        db_table = 'hotel_service_order_item'


class Payment(BaseModel):
    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, related_name='payments')
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    transaction_ref = models.CharField(max_length=100, blank=True, default='', db_index=True)
    vnp_transaction_no = models.CharField(max_length=32, blank=True, default='')
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_url = models.URLField(max_length=2000, blank=True, default='')
    gateway_meta = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'payments_payment'


class Invoice(BaseModel):
    invoice_number = models.CharField(max_length=30, unique=True)
    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, related_name='invoices')
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    issued_at = models.DateTimeField(auto_now_add=True)
    pdf_url = models.URLField(blank=True, default='')

    class Meta:
        db_table = 'payments_invoice'


class Transaction(BaseModel):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=[('credit', 'Credit'), ('debit', 'Debit')])
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    note = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'payments_transaction'


class HousekeepingTask(BaseModel):
    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name='housekeeping_tasks')
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='housekeeping_tasks',
    )
    status = models.CharField(max_length=20, choices=TaskStatus.choices, default=TaskStatus.PENDING)
    priority = models.CharField(max_length=10, choices=TaskPriority.choices, default=TaskPriority.NORMAL)
    task_type = models.CharField(max_length=20, choices=TaskType.choices, default=TaskType.CHECKOUT_CLEAN)
    notes = models.TextField(blank=True, default='')
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'housekeeping_task'
        indexes = [models.Index(fields=['assigned_to', 'status'])]


class HousekeepingLog(models.Model):
    id = models.BigAutoField(primary_key=True)
    task = models.ForeignKey(HousekeepingTask, on_delete=models.CASCADE, related_name='logs')
    action = models.CharField(max_length=50)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'housekeeping_log'
        ordering = ['-timestamp']


class Notification(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=30, choices=NotificationType.choices)
    title = models.CharField(max_length=255)
    body = models.TextField()
    channel = models.CharField(max_length=20, choices=NotificationChannel.choices, default=NotificationChannel.IN_APP)
    is_read = models.BooleanField(default=False)
    sent_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'notifications_notification'
        ordering = ['-sent_at']
