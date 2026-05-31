from django.db import transaction

from app.models import StaffProfile, User
from app.core.exceptions import BusinessException


class StaffService:
    @staticmethod
    @transaction.atomic
    def create_staff(data):
        role = data['role']
        if role not in [c[0] for c in User._meta.get_field('role').choices if c[0] != 'customer']:
            raise BusinessException('Role không hợp lệ', code='INVALID_ROLE')
        user = User.objects.create_user(
            email=data['email'],
            username=data['email'],
            password=data['password'],
            full_name=data['full_name'],
            phone=data.get('phone', ''),
            role=role,
            is_staff=True,
        )
        profile = StaffProfile.objects.create(
            user=user,
            employee_code=data['employee_code'],
            department=data.get('department', ''),
            hire_date=data.get('hire_date'),
        )
        return profile

    @staticmethod
    @transaction.atomic
    def deactivate_staff(user_id):
        user = User.objects.filter(pk=user_id).select_related('staff_profile').first()
        if not user or not hasattr(user, 'staff_profile'):
            raise BusinessException('Nhân viên không tồn tại', code='NOT_FOUND', status_code=404)
        user.is_active = False
        user.save(update_fields=['is_active'])
        return user.staff_profile

