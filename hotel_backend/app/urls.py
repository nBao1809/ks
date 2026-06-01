from django.urls import path

from app.views.accounts.views import (
    AvatarUploadView,
    ChangePasswordView,
    CustomerDetailView,
    CustomerListView,
    MeView,
    PasswordForgotView,
    PasswordResetView,
    RegisterView,
    StaffDetailView,
    StaffListCreateView,
)
from app.views.analytics.views import (
    BookingStatsView,
    DashboardView,
    OccupancyReportView,
    RevenueReportView,
    ServiceStatsView,
)
from app.views.bookings.views import (
    BookingCancelView,
    BookingCheckInView,
    BookingCheckOutView,
    BookingConfirmView,
    BookingDetailView,
    BookingListCreateView,
    BookingStatusHistoryView,
    BookingWalkInView,
    CustomerBookingsView,
)
from app.views.housekeeping.views import (
    HousekeepingHistoryView,
    HousekeepingTaskAssignView,
    HousekeepingTaskDetailView,
    HousekeepingTaskListCreateView,
    HousekeepingTaskLogView,
)
from app.views.notifications.views import (
    NotificationListView,
    NotificationReadAllView,
    NotificationReadView,
)
from app.views.payments.views import (
    InvoiceDetailView,
    InvoiceListCreateView,
    PaymentDetailView,
    PaymentListCreateView,
    PaymentRefundView,
    PaymentWebhookView,
    VNPayIPNView,
    VNPayReturnView,
)
from app.views.rooms.views import (
    AmenityDetailView,
    AmenityListCreateView,
    AvailabilityView,
    RoomDetailView,
    RoomListCreateView,
    RoomStatusUpdateView,
    RoomTypeDetailView,
    RoomTypeImageView,
    RoomTypeListCreateView,
    RoomTypePriceView,
)
from app.views.services.views import (
    BookingServiceOrdersView,
    ServiceCategoryListCreateView,
    ServiceDetailView,
    ServiceListCreateView,
    ServiceOrderCancelView,
    ServiceOrderConfirmView,
    ServiceOrderDetailView,
    ServiceOrderListCreateView,
)

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/password/forgot/', PasswordForgotView.as_view(), name='auth-password-forgot'),
    path('auth/password/reset/', PasswordResetView.as_view(), name='auth-password-reset'),
    path('auth/password/change/', ChangePasswordView.as_view(), name='auth-password-change'),
    path('auth/me/', MeView.as_view(), name='auth-me'),
    path('auth/me/avatar/', AvatarUploadView.as_view(), name='auth-avatar'),
    path('staff/', StaffListCreateView.as_view(), name='staff-list'),
    path('staff/<uuid:pk>/', StaffDetailView.as_view(), name='staff-detail'),
    path('customers/', CustomerListView.as_view(), name='customer-list'),
    path('customers/<uuid:pk>/', CustomerDetailView.as_view(), name='customer-detail'),
    path('customers/<uuid:pk>/bookings/', CustomerBookingsView.as_view(), name='customer-bookings'),

    path('room-types/', RoomTypeListCreateView.as_view(), name='room-type-list'),
    path('room-types/<uuid:pk>/', RoomTypeDetailView.as_view(), name='room-type-detail'),
    path('room-types/<uuid:pk>/images/', RoomTypeImageView.as_view(), name='room-type-images'),
    path('room-types/<uuid:pk>/prices/', RoomTypePriceView.as_view(), name='room-type-prices'),
    path('rooms/', RoomListCreateView.as_view(), name='room-list'),
    path('rooms/availability/', AvailabilityView.as_view(), name='room-availability'),
    path('rooms/<uuid:pk>/', RoomDetailView.as_view(), name='room-detail'),
    path('rooms/<uuid:pk>/status/', RoomStatusUpdateView.as_view(), name='room-status'),
    path('amenities/', AmenityListCreateView.as_view(), name='amenity-list'),
    path('amenities/<uuid:pk>/', AmenityDetailView.as_view(), name='amenity-detail'),

    path('bookings/', BookingListCreateView.as_view(), name='booking-list'),
    path('bookings/walk-in/', BookingWalkInView.as_view(), name='booking-walk-in'),
    path('bookings/<uuid:pk>/', BookingDetailView.as_view(), name='booking-detail'),
    path('bookings/<uuid:pk>/confirm/', BookingConfirmView.as_view(), name='booking-confirm'),
    path('bookings/<uuid:pk>/cancel/', BookingCancelView.as_view(), name='booking-cancel'),
    path('bookings/<uuid:pk>/check-in/', BookingCheckInView.as_view(), name='booking-check-in'),
    path('bookings/<uuid:pk>/check-out/', BookingCheckOutView.as_view(), name='booking-check-out'),
    path('bookings/<uuid:pk>/status-history/', BookingStatusHistoryView.as_view(), name='booking-status-history'),

    path('payments/', PaymentListCreateView.as_view(), name='payment-list'),
    path('payments/vnpay/ipn/', VNPayIPNView.as_view(), name='vnpay-ipn'),
    path('payments/vnpay/return/', VNPayReturnView.as_view(), name='vnpay-return'),
    path('payments/webhook/vnpay/', PaymentWebhookView.as_view(), name='payment-webhook'),
    path('payments/<uuid:pk>/', PaymentDetailView.as_view(), name='payment-detail'),
    path('payments/<uuid:pk>/refund/', PaymentRefundView.as_view(), name='payment-refund'),
    path('invoices/', InvoiceListCreateView.as_view(), name='invoice-list'),
    path('invoices/<uuid:pk>/', InvoiceDetailView.as_view(), name='invoice-detail'),

    path('service-categories/', ServiceCategoryListCreateView.as_view(), name='service-category-list'),
    path('services/', ServiceListCreateView.as_view(), name='service-list'),
    path('services/<uuid:pk>/', ServiceDetailView.as_view(), name='service-detail'),
    path('service-orders/', ServiceOrderListCreateView.as_view(), name='service-order-list'),
    path('service-orders/<uuid:pk>/', ServiceOrderDetailView.as_view(), name='service-order-detail'),
    path('service-orders/<uuid:pk>/confirm/', ServiceOrderConfirmView.as_view(), name='service-order-confirm'),
    path('service-orders/<uuid:pk>/cancel/', ServiceOrderCancelView.as_view(), name='service-order-cancel'),
    path('bookings/<uuid:booking_id>/service-orders/', BookingServiceOrdersView.as_view(), name='booking-service-orders'),

    path('housekeeping/tasks/', HousekeepingTaskListCreateView.as_view(), name='hk-task-list'),
    path('housekeeping/tasks/<uuid:pk>/', HousekeepingTaskDetailView.as_view(), name='hk-task-detail'),
    path('housekeeping/tasks/<uuid:pk>/assign/', HousekeepingTaskAssignView.as_view(), name='hk-task-assign'),
    path('housekeeping/tasks/<uuid:pk>/logs/', HousekeepingTaskLogView.as_view(), name='hk-task-logs'),
    path('housekeeping/history/', HousekeepingHistoryView.as_view(), name='hk-history'),

    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('notifications/read-all/', NotificationReadAllView.as_view(), name='notification-read-all'),
    path('notifications/<uuid:pk>/read/', NotificationReadView.as_view(), name='notification-read'),

    path('analytics/revenue/', RevenueReportView.as_view(), name='analytics-revenue'),
    path('analytics/occupancy/', OccupancyReportView.as_view(), name='analytics-occupancy'),
    path('analytics/bookings/', BookingStatsView.as_view(), name='analytics-bookings'),
    path('analytics/services/', ServiceStatsView.as_view(), name='analytics-services'),
    path('analytics/dashboard/', DashboardView.as_view(), name='analytics-dashboard'),
]
