from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from app.permissions import CanManageStaff
from app.core.schema import (
    AvatarResponseSerializer,
    MessageSerializer,
    PasswordForgotResponseSerializer,
    StaffUpdateSerializer,
)
from app.serializers.accounts import (
    ChangePasswordSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    StaffCreateSerializer,
    StaffSerializer,
    UserProfileSerializer,
    UserSerializer,
)
from app.views.accounts.services.auth_service import AuthService
from app.views.accounts.services.staff_service import StaffService
from app.models import StaffProfile, User
from app.permissions import IsManager
from app.core.schema import PARAM_PAGE, PARAM_PAGE_SIZE, PARAM_SEARCH, TAG_AUTH, TAG_CUSTOMERS, TAG_STAFF


@extend_schema_view(
    post=extend_schema(
        tags=[TAG_AUTH],
        summary='Đăng ký tài khoản khách hàng',
        description='Tạo tài khoản Customer mới. Không cần đăng nhập.',
        request=RegisterSerializer,
        responses={201: UserSerializer},
        auth=[],
        examples=[
            OpenApiExample(
                'Customer mới',
                value={
                    'email': 'newcustomer@example.com',
                    'password': 'SecurePass123!',
                    'password_confirm': 'SecurePass123!',
                    'full_name': 'Nguyen Van A',
                    'phone': '0901234567',
                },
                request_only=True,
            ),
        ],
    ),
)
class RegisterView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = AuthService.register_customer(
            email=data['email'],
            password=data['password'],
            full_name=data['full_name'],
            phone=data.get('phone', ''),
            avatar=data.get('avatar'),
        )
        return Response(UserSerializer(user, context={'request': request}).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    post=extend_schema(
        tags=[TAG_AUTH],
        summary='Đổi mật khẩu',
        request=ChangePasswordSerializer,
        responses={200: MessageSerializer},
    ),
)
class ChangePasswordView(APIView):
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        AuthService.change_password(request.user, serializer.validated_data['new_password'])
        return Response({'message': 'Đổi mật khẩu thành công'})


@extend_schema_view(
    post=extend_schema(
        tags=[TAG_AUTH],
        summary='Quên mật khẩu',
        description='Gửi email reset (dev: thêm ?debug=1 để nhận token trong response).',
        request=PasswordResetRequestSerializer,
        responses={200: PasswordForgotResponseSerializer},
        parameters=[
            OpenApiParameter(name='debug', type=str, location=OpenApiParameter.QUERY, required=False, description='debug=1 trả token'),
        ],
        auth=[],
    ),
)
class PasswordForgotView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        raw_token = AuthService.request_password_reset(serializer.validated_data['email'])
        payload = {'message': 'Nếu email tồn tại, link đặt lại mật khẩu đã được gửi'}
        if raw_token and request.query_params.get('debug') == '1':
            payload['token'] = raw_token
        return Response(payload)


@extend_schema_view(
    post=extend_schema(
        tags=[TAG_AUTH],
        summary='Đặt lại mật khẩu',
        request=PasswordResetConfirmSerializer,
        responses={200: MessageSerializer},
        auth=[],
    ),
)
class PasswordResetView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AuthService.reset_password(
            serializer.validated_data['token'],
            serializer.validated_data['new_password'],
        )
        return Response({'message': 'Đổi mật khẩu thành công'})


@extend_schema_view(
    get=extend_schema(
        tags=[TAG_AUTH],
        summary='Xem profile hiện tại',
        responses={200: UserSerializer},
    ),
    patch=extend_schema(
        tags=[TAG_AUTH],
        summary='Cập nhật profile',
        request=UserProfileSerializer,
        responses={200: UserSerializer},
    ),
)
class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user, context={'request': request}).data)

    def patch(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user, context={'request': request}).data)


@extend_schema_view(
    post=extend_schema(
        tags=[TAG_AUTH],
        summary='Upload avatar',
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'avatar': {'type': 'string', 'format': 'binary', 'description': 'jpg/png, max 5MB'},
                },
                'required': ['avatar'],
            },
        },
        responses={200: AvatarResponseSerializer},
    ),
)
class AvatarUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        avatar = request.FILES.get('avatar')
        if not avatar:
            return Response({'avatar': ['File avatar là bắt buộc']}, status=status.HTTP_400_BAD_REQUEST)
        request.user.avatar = avatar
        request.user.save(update_fields=['avatar'])
        url = request.build_absolute_uri(request.user.avatar.url)
        return Response({'avatar': url})


@extend_schema_view(
    get=extend_schema(
        tags=[TAG_STAFF],
        summary='Danh sách nhân viên',
        parameters=[
            PARAM_PAGE,
            PARAM_PAGE_SIZE,
            PARAM_SEARCH,
            OpenApiParameter(name='role', type=str, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={200: StaffSerializer(many=True)},
    ),
    post=extend_schema(
        tags=[TAG_STAFF],
        summary='Tạo nhân viên',
        request=StaffCreateSerializer,
        responses={201: StaffSerializer},
    ),
)
class StaffListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsManager()]
        return [CanManageStaff()]

    def get(self, request):
        qs = StaffProfile.objects.select_related('user').filter(user__is_active=True)
        role = request.query_params.get('role')
        if role:
            qs = qs.filter(user__role=role)
        search = request.query_params.get('search')
        if search:
            qs = qs.filter(user__full_name__icontains=search) | qs.filter(user__email__icontains=search)
        page = int(request.query_params.get('page', 1))
        page_size = min(int(request.query_params.get('page_size', 20)), 100)
        total = qs.count()
        start = (page - 1) * page_size
        items = qs.order_by('-user__date_joined')[start:start + page_size]
        return Response({
            'data': StaffSerializer(items, many=True).data,
            'meta': {
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size if page_size else 0,
                'total_count': total,
            },
        })

    def post(self, request):
        serializer = StaffCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = StaffService.create_staff(serializer.validated_data)
        return Response(StaffSerializer(profile).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(tags=[TAG_STAFF], summary='Chi tiết nhân viên', responses={200: StaffSerializer}),
    patch=extend_schema(tags=[TAG_STAFF], summary='Cập nhật nhân viên', request=StaffUpdateSerializer, responses={200: StaffSerializer}),
    delete=extend_schema(tags=[TAG_STAFF], summary='Vô hiệu hóa nhân viên', responses={204: None}),
)
class StaffDetailView(APIView):
    permission_classes = [IsManager]

    def get_object(self, pk):
        return StaffProfile.objects.select_related('user').filter(user_id=pk).first()

    def get(self, request, pk):
        profile = self.get_object(pk)
        if not profile:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(StaffSerializer(profile).data)

    def patch(self, request, pk):
        profile = self.get_object(pk)
        if not profile:
            return Response(status=status.HTTP_404_NOT_FOUND)
        user = profile.user
        for field in ('full_name', 'phone'):
            if field in request.data:
                setattr(user, field, request.data[field])
        for field in ('department', 'hire_date'):
            if field in request.data:
                setattr(profile, field, request.data[field])
        user.save()
        profile.save()
        return Response(StaffSerializer(profile).data)

    def delete(self, request, pk):
        profile = self.get_object(pk)
        if not profile:
            return Response(status=status.HTTP_404_NOT_FOUND)
        StaffService.deactivate_staff(pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    get=extend_schema(
        tags=[TAG_CUSTOMERS],
        summary='Danh sách khách hàng',
        parameters=[PARAM_PAGE, PARAM_PAGE_SIZE, PARAM_SEARCH],
        responses={200: UserSerializer(many=True)},
    ),
)
class CustomerListView(APIView):
    permission_classes = [CanManageStaff]

    def get(self, request):
        qs = User.objects.filter(role='customer', is_active=True)
        search = request.query_params.get('search')
        if search:
            qs = qs.filter(full_name__icontains=search) | qs.filter(email__icontains=search)
        page = int(request.query_params.get('page', 1))
        page_size = min(int(request.query_params.get('page_size', 20)), 100)
        total = qs.count()
        start = (page - 1) * page_size
        items = qs.order_by('-date_joined')[start:start + page_size]
        return Response({
            'data': UserSerializer(items, many=True, context={'request': request}).data,
            'meta': {
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size if page_size else 0,
                'total_count': total,
            },
        })


@extend_schema_view(
    get=extend_schema(tags=[TAG_CUSTOMERS], summary='Chi tiết khách hàng', responses={200: UserSerializer}),
)
class CustomerDetailView(APIView):
    permission_classes = [CanManageStaff]

    def get(self, request, pk):
        user = User.objects.filter(pk=pk, role='customer').first()
        if not user:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(UserSerializer(user, context={'request': request}).data)




