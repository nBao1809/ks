import hashlib
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from app.core.exceptions import BusinessException
from app.models import UserRole
from app.models import PasswordResetToken, User


logger = logging.getLogger(__name__)


class AuthService:
    @staticmethod
    @transaction.atomic
    def register_customer(email, password, full_name, phone='', avatar=None):
        user = User.objects.create_user(
            email=email,
            username=email,
            password=password,
            full_name=full_name,
            phone=phone,
            role=UserRole.CUSTOMER,
        )
        if avatar:
            user.avatar = avatar
            user.save(update_fields=['avatar'])
        return user

    @staticmethod
    @transaction.atomic
    def change_password(user, new_password):
        user.set_password(new_password)
        user.save(update_fields=['password'])

    @staticmethod
    @transaction.atomic
    def request_password_reset(email):
        user = User.objects.filter(email=email, is_active=True).first()
        if not user:
            logger.info('Password reset requested for unknown/inactive email: %s', email)
            return None
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        PasswordResetToken.objects.filter(user=user, used=False).update(used=True)
        PasswordResetToken.objects.create(
            user=user,
            token_hash=token_hash,
            expires_at=timezone.now() + timedelta(hours=24),
        )
        AuthService._send_reset_email(user, raw_token)
        return raw_token

    @staticmethod
    def _send_reset_email(user, raw_token):
        """Gửi email đặt lại mật khẩu. Khi DEBUG=True dùng console backend."""
        subject = '[Smart Hotel] Đặt lại mật khẩu'
        message = (
            f'Xin chào {user.full_name},\n\n'
            f'Chúng tôi nhận được yêu cầu đặt lại mật khẩu cho tài khoản của bạn.\n\n'
            f'Mã token của bạn (có hiệu lực trong 24 giờ):\n\n'
            f'    {raw_token}\n\n'
            f'Nhập mã này vào màn hình "Đặt lại mật khẩu" trong ứng dụng.\n\n'
            f'Nếu bạn không yêu cầu đặt lại mật khẩu, hãy bỏ qua email này.\n\n'
            f'Trân trọng,\nĐội ngũ Smart Hotel'
        )
        try:
            sent_count = send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            logger.info(
                'Password reset email backend=%s recipient=%s sent_count=%s',
                settings.EMAIL_BACKEND,
                user.email,
                sent_count,
            )
        except Exception:
            # Forgot-password should not fail hard if email provider is misconfigured.
            logger.exception(
                'Password reset email send failed backend=%s recipient=%s',
                settings.EMAIL_BACKEND,
                user.email,
            )

    @staticmethod
    @transaction.atomic
    def reset_password(raw_token, new_password):
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        reset = PasswordResetToken.objects.select_related('user').filter(
            token_hash=token_hash,
            used=False,
            expires_at__gte=timezone.now(),
        ).first()
        if not reset:
            raise BusinessException('Token không hợp lệ hoặc đã hết hạn', code='INVALID_TOKEN')
        reset.user.set_password(new_password)
        reset.user.save(update_fields=['password'])
        reset.used = True
        reset.save(update_fields=['used'])

