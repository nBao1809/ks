from rest_framework import serializers

from app.serializers.accounts import (
    ChangePasswordSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    StaffCreateSerializer,
    StaffSerializer,
    UserProfileSerializer,
    UserSerializer,
)


class RefreshTokenSerializer(serializers.Serializer):
    refresh = serializers.CharField(help_text='Refresh token nhận sau khi login')


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(help_text='Refresh token cần blacklist khi logout')


class MessageSerializer(serializers.Serializer):
    message = serializers.CharField()


class PasswordForgotResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    token = serializers.CharField(required=False, help_text='Chỉ trả khi ?debug=1')


class LoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()


class TokenRefreshResponseSerializer(serializers.Serializer):
    access = serializers.CharField(help_text='JWT access token mới')


class TokenRefreshRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField(help_text='Refresh token từ login')


class AvatarResponseSerializer(serializers.Serializer):
    avatar = serializers.URLField()


class StaffUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(required=False)
    phone = serializers.CharField(required=False)
    department = serializers.CharField(required=False)
    hire_date = serializers.DateField(required=False)


AUTH_REGISTER = RegisterSerializer
AUTH_LOGIN = LoginSerializer
AUTH_REFRESH = RefreshTokenSerializer
AUTH_LOGOUT = LogoutSerializer
AUTH_CHANGE_PASSWORD = ChangePasswordSerializer
AUTH_FORGOT = PasswordResetRequestSerializer
AUTH_RESET = PasswordResetConfirmSerializer
AUTH_ME_PATCH = UserProfileSerializer


