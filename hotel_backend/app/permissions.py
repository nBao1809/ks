from rest_framework.permissions import SAFE_METHODS, BasePermission

from app.models import Booking, RoomStatus, UserRole


class IsRole(BasePermission):
    role = None

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return request.user.role == self.role


class IsManager(IsRole):
    role = UserRole.MANAGER


class IsReceptionist(IsRole):
    role = UserRole.RECEPTIONIST


class IsHousekeeping(IsRole):
    role = UserRole.HOUSEKEEPING


class IsCustomer(IsRole):
    role = UserRole.CUSTOMER


class IsStaff(BasePermission):
    staff_roles = (
        UserRole.MANAGER,
        UserRole.RECEPTIONIST,
        UserRole.HOUSEKEEPING,
    )

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return request.user.role in self.staff_roles


class IsManagerOrReceptionist(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return request.user.role in (UserRole.MANAGER, UserRole.RECEPTIONIST)


class IsStaffManager(IsManager):
    pass


class CanManageStaff(IsManager):
    pass


class CanViewCustomers(IsRole):
    role = UserRole.RECEPTIONIST

    def has_permission(self, request, view):
        if super().has_permission(request, view):
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return request.user.role == UserRole.MANAGER


class RoomPermission(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return IsManager().has_permission(request, view)


class RoomStatusPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return request.user.role in (
            UserRole.MANAGER,
            UserRole.RECEPTIONIST,
            UserRole.HOUSEKEEPING,
        )

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        role = request.user.role
        if role in (UserRole.MANAGER, UserRole.RECEPTIONIST):
            return True
        if role == UserRole.HOUSEKEEPING:
            new_status = request.data.get('status')
            if new_status == RoomStatus.AVAILABLE and obj.status == RoomStatus.CLEANING:
                return True
            return False
        return False


class AmenityPermission(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return IsManager().has_permission(request, view)


class BookingAccessPermission(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        if request.user.role in (UserRole.MANAGER, UserRole.RECEPTIONIST):
            return True
        if request.user.role == UserRole.CUSTOMER:
            return obj.customer_id == request.user.id
        return False


class BookingStaffActionPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return request.user.role in (UserRole.MANAGER, UserRole.RECEPTIONIST)
