from datetime import date, datetime

from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework.response import Response
from rest_framework.views import APIView

from app.serializers.analytics import (
    BookingStatsSerializer,
    DashboardSerializer,
    OccupancyReportSerializer,
    RevenueReportSerializer,
    ServiceStatsSerializer,
)
from app.views.analytics.services.report_service import ReportService
from app.permissions import IsManager
from app.core.schema import TAG_ANALYTICS


@extend_schema_view(
    get=extend_schema(
        tags=[TAG_ANALYTICS],
        summary='Báo cáo doanh thu',
        parameters=[
            OpenApiParameter(name='period', type=str, location=OpenApiParameter.QUERY, description='day|month|quarter|year'),
            OpenApiParameter(name='year', type=int, location=OpenApiParameter.QUERY),
            OpenApiParameter(name='month', type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name='quarter', type=int, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={200: RevenueReportSerializer},
    ),
)
class RevenueReportView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        period = request.query_params.get('period', 'month')
        year = int(request.query_params.get('year', date.today().year))
        month = request.query_params.get('month')
        quarter = request.query_params.get('quarter')
        return Response(ReportService.revenue(
            period, year,
            month=int(month) if month else None,
            quarter=int(quarter) if quarter else None,
        ))


@extend_schema_view(
    get=extend_schema(
        tags=[TAG_ANALYTICS],
        summary='Tỷ lệ lấp phòng',
        parameters=[
            OpenApiParameter(name='from', type=str, location=OpenApiParameter.QUERY, required=True),
            OpenApiParameter(name='to', type=str, location=OpenApiParameter.QUERY, required=True),
        ],
    ),
)
class OccupancyReportView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        dfrom = datetime.strptime(request.query_params['from'], '%Y-%m-%d').date()
        dto = datetime.strptime(request.query_params['to'], '%Y-%m-%d').date()
        return Response(ReportService.occupancy(dfrom, dto))


@extend_schema_view(
    get=extend_schema(
        tags=[TAG_ANALYTICS],
        summary='Thống kê booking',
        parameters=[
            OpenApiParameter(name='period', type=str, location=OpenApiParameter.QUERY),
            OpenApiParameter(name='year', type=int, location=OpenApiParameter.QUERY),
            OpenApiParameter(name='quarter', type=int, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={200: BookingStatsSerializer},
    ),
)
class BookingStatsView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        period = request.query_params.get('period', 'quarter')
        year = int(request.query_params.get('year', date.today().year))
        quarter = request.query_params.get('quarter')
        return Response(ReportService.booking_stats(
            period, year, quarter=int(quarter) if quarter else None,
        ))


@extend_schema_view(
    get=extend_schema(
        tags=[TAG_ANALYTICS],
        summary='Thống kê dịch vụ',
        parameters=[
            OpenApiParameter(name='period', type=str, location=OpenApiParameter.QUERY),
            OpenApiParameter(name='year', type=int, location=OpenApiParameter.QUERY),
            OpenApiParameter(name='month', type=int, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={200: ServiceStatsSerializer},
    ),
)
class ServiceStatsView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        period = request.query_params.get('period', 'month')
        year = int(request.query_params.get('year', date.today().year))
        month = request.query_params.get('month')
        return Response(ReportService.service_stats(
            period, year, month=int(month) if month else None,
        ))


@extend_schema_view(
    get=extend_schema(
        tags=[TAG_ANALYTICS],
        summary='Dashboard tổng hợp',
        parameters=[OpenApiParameter(name='date', type=str, location=OpenApiParameter.QUERY, required=False)],
        responses={200: DashboardSerializer},
    ),
)
class DashboardView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        d = request.query_params.get('date')
        target = datetime.strptime(d, '%Y-%m-%d').date() if d else date.today()
        return Response(ReportService.dashboard(target))



