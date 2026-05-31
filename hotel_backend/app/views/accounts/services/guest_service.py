import uuid

from django.db import transaction

from app.models import UserRole
from app.models import GuestProfile, User
from app.core.exceptions import BusinessException


class GuestService:
    @staticmethod
    @transaction.atomic
    def create_walk_in_guest(full_name, national_id, phone='', email='', address='', notes=''):
        national_id = (national_id or '').strip()
        if not full_name or not national_id:
            raise BusinessException('Họ tên và CCCD/Passport là bắt buộc', code='VALIDATION_ERROR')

        if national_id:
            profile = (
                GuestProfile.objects.select_related('user')
                .filter(national_id=national_id, user__is_active=True)
                .first()
            )
            if profile:
                user = profile.user
                user.full_name = full_name
                if phone:
                    user.phone = phone
                user.save(update_fields=['full_name', 'phone', 'updated_at'])
                profile.address = address or profile.address
                profile.notes = notes or profile.notes
                profile.save(update_fields=['address', 'notes', 'updated_at'])
                return user

        email = (email or '').strip().lower()
        if email:
            if User.objects.filter(email=email).exists():
                raise BusinessException('Email đã được sử dụng', code='EMAIL_EXISTS', status_code=409)
        else:
            email = f'walkin-{uuid.uuid4().hex[:12]}@guest.local'

        user = User(
            email=email,
            username=email,
            role=UserRole.CUSTOMER,
            full_name=full_name.strip(),
            phone=(phone or '').strip(),
            is_active=True,
        )
        user.set_unusable_password()
        user.save()

        GuestProfile.objects.create(
            user=user,
            national_id=national_id,
            address=(address or '').strip(),
            notes=(notes or '').strip(),
            is_temporary=True,
        )
        return user
