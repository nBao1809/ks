from drf_spectacular.utils import OpenApiParameter

TAG_AUTH = 'Auth'
TAG_STAFF = 'Staff'
TAG_CUSTOMERS = 'Customers'
TAG_ROOM_TYPES = 'Room Types'
TAG_ROOMS = 'Rooms'
TAG_AMENITIES = 'Amenities'
TAG_HEALTH = 'Health'
TAG_BOOKINGS = 'Bookings'
TAG_PAYMENTS = 'Payments'
TAG_INVOICES = 'Invoices'
TAG_SERVICES = 'Hotel Services'
TAG_HOUSEKEEPING = 'Housekeeping'
TAG_NOTIFICATIONS = 'Notifications'
TAG_ANALYTICS = 'Analytics'

PARAM_PAGE = OpenApiParameter(name='page', type=int, location=OpenApiParameter.QUERY, description='Trang (mặc định 1)')
PARAM_PAGE_SIZE = OpenApiParameter(
    name='page_size', type=int, location=OpenApiParameter.QUERY, description='Số bản ghi/trang (max 100)',
)
PARAM_SEARCH = OpenApiParameter(name='search', type=str, location=OpenApiParameter.QUERY, required=False)
