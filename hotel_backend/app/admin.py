from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from app.models import (
    Amenity,
    Booking,
    BookingRoom,
    BookingStatusHistory,
    HousekeepingLog,
    HousekeepingTask,
    Invoice,
    Notification,
    PasswordResetToken,
    Payment,
    Room,
    RoomPrice,
    RoomType,
    RoomTypeImage,
    Service,
    ServiceCategory,
    ServiceOrder,
    ServiceOrderItem,
    StaffProfile,
    Transaction,
    User,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'full_name', 'role', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('email', 'full_name', 'phone')
    ordering = ('-date_joined',)
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Profile', {'fields': ('role', 'phone', 'full_name', 'avatar', 'email_verified')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Profile', {'fields': ('role', 'phone', 'full_name')}),
    )


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ('employee_code', 'user', 'department', 'hire_date')
    search_fields = ('employee_code', 'user__email', 'user__full_name')


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'expires_at', 'used', 'created_at')
    list_filter = ('used',)


class BookingRoomInline(admin.TabularInline):
    model = BookingRoom
    extra = 0


class BookingStatusHistoryInline(admin.TabularInline):
    model = BookingStatusHistory
    extra = 0
    readonly_fields = ('from_status', 'to_status', 'changed_by', 'changed_at', 'note')


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('booking_code', 'customer', 'status', 'check_in_date', 'check_out_date', 'total_amount')
    list_filter = ('status',)
    search_fields = ('booking_code', 'customer__email')
    inlines = [BookingRoomInline, BookingStatusHistoryInline]


class RoomTypeImageInline(admin.TabularInline):
    model = RoomTypeImage
    extra = 1


class RoomInline(admin.TabularInline):
    model = Room
    extra = 0


@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'max_occupancy', 'base_price', 'is_active')
    search_fields = ('name',)
    filter_horizontal = ('amenities',)
    inlines = [RoomTypeImageInline, RoomInline]


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('room_number', 'floor', 'room_type', 'status', 'is_active')
    list_filter = ('status', 'floor', 'room_type')
    search_fields = ('room_number',)


@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'is_active')


@admin.register(RoomPrice)
class RoomPriceAdmin(admin.ModelAdmin):
    list_display = ('room_type', 'price', 'valid_from', 'valid_to', 'is_active')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'booking', 'amount', 'method', 'status', 'paid_at')
    list_filter = ('status', 'method')


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'booking', 'total', 'issued_at')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('payment', 'transaction_type', 'amount', 'created_at')


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active')


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'unit', 'is_active')


class ServiceOrderItemInline(admin.TabularInline):
    model = ServiceOrderItem
    extra = 0


@admin.register(ServiceOrder)
class ServiceOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'booking', 'customer', 'status', 'total_amount')
    inlines = [ServiceOrderItemInline]


class HousekeepingLogInline(admin.TabularInline):
    model = HousekeepingLog
    extra = 0


@admin.register(HousekeepingTask)
class HousekeepingTaskAdmin(admin.ModelAdmin):
    list_display = ('room', 'assigned_to', 'status', 'priority', 'task_type')
    list_filter = ('status', 'priority')
    inlines = [HousekeepingLogInline]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'title', 'is_read', 'sent_at')
    list_filter = ('notification_type', 'is_read')
