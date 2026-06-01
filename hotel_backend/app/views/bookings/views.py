from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from app.models import UserRole
from app.permissions import CanManageStaff
from app.models import Booking, BookingStatus
from app.permissions import BookingAccessPermission, BookingStaffActionPermission
from app.serializers.bookings import (
    BookingActionNoteSerializer,
    BookingCancelSerializer,
    BookingCheckInSerializer,
    BookingCreateSerializer,
    BookingDetailSerializer,
    BookingListSerializer,
    BookingStatusHistorySerializer,
    BookingWalkInSerializer,
)
from app.views.bookings.services.booking_service import BookingService
from app.core.pagination import StandardPagination
from app.core.schema import PARAM_PAGE, PARAM_PAGE_SIZE, PARAM_SEARCH, TAG_BOOKINGS
from app.models import PaymentMethod
from app.serializers.payments import PaymentSerializer
from app.views.payments.services.payment_service import PaymentService

BOOKING_LIST_PARAMS = [
    PARAM_PAGE,
    PARAM_PAGE_SIZE,
    PARAM_SEARCH,
    OpenApiParameter(name='status', type=str, location=OpenApiParameter.QUERY, required=False),
    OpenApiParameter(
        name='status__in',
        type=str,
        location=OpenApiParameter.QUERY,
        required=False,
        description='Lọc nhiều trạng thái, phân tách bằng dấu phẩy (VD: pending,confirmed,checked_in)',
    ),
    OpenApiParameter(name='check_in_date', type=str, location=OpenApiParameter.QUERY, required=False),
    OpenApiParameter(name='customer_id', type=str, location=OpenApiParameter.QUERY, required=False),
]


@extend_schema_view(
    get=extend_schema(
        tags=[TAG_BOOKINGS],
        summary='Danh sách booking',
        parameters=BOOKING_LIST_PARAMS,
        responses={200: BookingListSerializer(many=True)},
    ),
    post=extend_schema(
        tags=[TAG_BOOKINGS],
        summary='Đặt phòng online (Customer)',
        request=BookingCreateSerializer,
        responses={201: BookingDetailSerializer},
        examples=[
            OpenApiExample(
                'Đặt 1 phòng Deluxe',
                value={
                    'check_in_date': '2026-06-01',
                    'check_out_date': '2026-06-05',
                    'adults': 2,
                    'children': 0,
                    'payment_method': 'vnpay',
                    'rooms': [{'room_type_id': '00000000-0000-0000-0000-000000000001', 'quantity': 1}],
                    'special_request': 'Giường đôi',
                },
                request_only=True,
            ),
        ],
    ),
)
class BookingListCreateView(APIView):
    permission_classes = [BookingAccessPermission]

    def get(self, request):
        qs = BookingService.get_queryset_for_user(request.user)
        status_in = request.query_params.get('status__in')
        if status_in:
            statuses = [s.strip() for s in status_in.split(',') if s.strip()]
            if statuses:
                qs = qs.filter(status__in=statuses)
        else:
            status_param = request.query_params.get('status')
            if status_param:
                qs = qs.filter(status=status_param)
        check_in = request.query_params.get('check_in_date')
        if check_in:
            qs = qs.filter(check_in_date=check_in)
        check_in_gte = request.query_params.get('check_in_date_gte')
        if check_in_gte:
            qs = qs.filter(check_in_date__gte=check_in_gte)
        customer_id = request.query_params.get('customer_id')
        if customer_id and request.user.role in (UserRole.MANAGER, UserRole.RECEPTIONIST):
            qs = qs.filter(customer_id=customer_id)
        search = request.query_params.get('search')
        if search:
            qs = qs.filter(booking_code__icontains=search)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs.order_by('-created_at'), request)
        return paginator.get_paginated_response(BookingListSerializer(page, many=True).data)

    def post(self, request):
        if request.user.role != UserRole.CUSTOMER and not request.user.is_superuser:
            return Response({'detail': 'Chỉ customer đặt online qua endpoint này'}, status=403)
        serializer = BookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        booking = BookingService.create_booking(
            customer=request.user,
            check_in=data['check_in_date'],
            check_out=data['check_out_date'],
            adults=data['adults'],
            children=data['children'],
            rooms_data=data['rooms'],
            special_request=data.get('special_request', ''),
        )

        payment_method = data.get('payment_method', 'vnpay')
        payment = None
        message = ''

        if payment_method == 'vnpay':
            payment = PaymentService.create_payment(
                booking.id,
                booking.total_amount,
                PaymentMethod.VNPAY,
                request.user,
                request=request,
                app_return_url=data.get('app_return_url', ''),
            )
            message = 'Đơn đặt phòng đã được tạo. Vui lòng thanh toán VNPay để xác nhận.'
        else:
            message = 'Đơn đặt phòng đã được tạo ở trạng thái chờ xác nhận. Vui lòng thanh toán tại quầy khi đến khách sạn.'

        return Response({
            'booking': BookingDetailSerializer(booking).data,
            'payment_method': payment_method,
            'payment': PaymentSerializer(payment).data if payment else None,
            'payment_url': payment.payment_url if payment else '',
            'message': message,
        }, status=status.HTTP_201_CREATED)


@extend_schema_view(
    post=extend_schema(
        tags=[TAG_BOOKINGS],
        summary='Tạo booking walk-in (Lễ tân)',
        request=BookingWalkInSerializer,
        responses={201: BookingDetailSerializer},
    ),
)
class BookingWalkInView(APIView):
    permission_classes = [BookingStaffActionPermission]

    def post(self, request):
        serializer = BookingWalkInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        booking = BookingService.create_walk_in(
            staff=request.user,
            customer_id=data.get('customer_id'),
            guest_data=data.get('guest'),
            check_in=data['check_in_date'],
            check_out=data['check_out_date'],
            adults=data['adults'],
            children=data['children'],
            room_ids=data['room_ids'],
            special_request=data.get('special_request', ''),
            status=data.get('status'),
        )
        return Response(BookingDetailSerializer(booking).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(tags=[TAG_BOOKINGS], summary='Chi tiết booking', responses={200: BookingDetailSerializer}),
)
class BookingDetailView(APIView):
    permission_classes = [BookingAccessPermission]

    def get(self, request, pk):
        booking = get_object_or_404(BookingService.get_queryset_for_user(request.user), pk=pk)
        return Response(BookingDetailSerializer(booking).data)


@extend_schema_view(
    post=extend_schema(tags=[TAG_BOOKINGS], summary='Xác nhận booking', request=BookingActionNoteSerializer, responses={200: BookingDetailSerializer}),
)
class BookingConfirmView(APIView):
    permission_classes = [BookingStaffActionPermission]

    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk, is_active=True)
        note = request.data.get('note', '')
        booking = BookingService.transition(booking, BookingStatus.CONFIRMED, request.user, note)
        return Response(BookingDetailSerializer(booking).data)


@extend_schema_view(
    post=extend_schema(tags=[TAG_BOOKINGS], summary='Hủy booking', request=BookingCancelSerializer, responses={200: BookingDetailSerializer}),
)
class BookingCancelView(APIView):
    permission_classes = [BookingAccessPermission]

    def post(self, request, pk):
        booking = get_object_or_404(BookingService.get_queryset_for_user(request.user), pk=pk)
        serializer = BookingCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = BookingService.transition(
            booking, BookingStatus.CANCELLED, request.user, serializer.validated_data.get('reason', ''),
        )
        return Response(BookingDetailSerializer(booking).data)


@extend_schema_view(
    post=extend_schema(tags=[TAG_BOOKINGS], summary='Check-in', request=BookingCheckInSerializer, responses={200: BookingDetailSerializer}),
)
class BookingCheckInView(APIView):
    permission_classes = [BookingStaffActionPermission]

    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk, is_active=True)
        serializer = BookingCheckInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        from app.views.accounts.services.guest_service import GuestService
        GuestService.upsert_profile_for_customer(
            booking.customer,
            national_id=data['national_id'],
            address=data['address'],
            notes=data.get('note', ''),
        )
        note = data.get('note', '')
        booking = BookingService.transition(booking, BookingStatus.CHECKED_IN, request.user, note)
        return Response(BookingDetailSerializer(booking).data)


@extend_schema_view(
    post=extend_schema(tags=[TAG_BOOKINGS], summary='Check-out', request=BookingActionNoteSerializer, responses={200: BookingDetailSerializer}),
)
class BookingCheckOutView(APIView):
    permission_classes = [BookingStaffActionPermission]

    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk, is_active=True)
        note = request.data.get('note', '')
        booking = BookingService.transition(booking, BookingStatus.CHECKED_OUT, request.user, note)
        return Response(BookingDetailSerializer(booking).data)


@extend_schema_view(
    get=extend_schema(tags=[TAG_BOOKINGS], summary='Lịch sử trạng thái booking', responses={200: BookingStatusHistorySerializer(many=True)}),
)
@extend_schema_view(
    get=extend_schema(tags=[TAG_BOOKINGS], summary='Lịch sử booking của khách', responses={200: BookingListSerializer(many=True)}),
)
class CustomerBookingsView(APIView):
    permission_classes = [CanManageStaff]

    def get(self, request, pk):
        qs = BookingService.get_queryset_for_user(request.user).filter(customer_id=pk)
        return Response(BookingListSerializer(qs.order_by('-created_at'), many=True).data)


@extend_schema_view(
    get=extend_schema(tags=[TAG_BOOKINGS], summary='Lịch sử trạng thái booking', responses={200: BookingStatusHistorySerializer(many=True)}),
)
class BookingStatusHistoryView(APIView):
    permission_classes = [BookingAccessPermission]

    def get(self, request, pk):
        booking = get_object_or_404(BookingService.get_queryset_for_user(request.user), pk=pk)
        history = booking.status_history.select_related('changed_by')
        return Response(BookingStatusHistorySerializer(history, many=True).data)




