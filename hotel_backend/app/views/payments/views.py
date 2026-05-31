import json

from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from app.core.pagination import StandardPagination
from app.permissions import IsManager, IsManagerOrReceptionist
from app.core.schema import PARAM_PAGE, PARAM_PAGE_SIZE, TAG_INVOICES, TAG_PAYMENTS
from app.models import Invoice
from app.serializers.payments import (
    InvoiceSerializer,
    PaymentCreateSerializer,
    PaymentRefundSerializer,
    PaymentSerializer,
    PaymentWebhookSerializer,
    VNPayReturnSerializer,
)
from app.views.payments.services.payment_service import PaymentService
from app.views.payments.services.vnpay_service import VNPayService


class AppRedirect(HttpResponseRedirect):
    allowed_schemes = [*HttpResponseRedirect.allowed_schemes, 'smarthotelapp', 'exp']


@extend_schema_view(
    get=extend_schema(
        tags=[TAG_PAYMENTS],
        summary='Danh sách thanh toán',
        parameters=[
            PARAM_PAGE,
            PARAM_PAGE_SIZE,
            OpenApiParameter(name='booking_id', type=str, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name='status', type=str, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={200: PaymentSerializer(many=True)},
    ),
    post=extend_schema(
        tags=[TAG_PAYMENTS],
        summary='Tạo thanh toán',
        request=PaymentCreateSerializer,
        responses={201: PaymentSerializer},
        examples=[
            OpenApiExample('Tiền mặt', value={'booking_id': 'uuid', 'amount': '10000000.00', 'method': 'cash'}, request_only=True),
            OpenApiExample('VNPay', value={'booking_id': 'uuid', 'amount': '10000000.00', 'method': 'vnpay'}, request_only=True),
        ],
    ),
)
class PaymentListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        booking_id = request.query_params.get('booking_id')
        qs = PaymentService.get_payments_for_user(request.user, booking_id)
        status_param = request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs.order_by('-created_at'), request)
        return paginator.get_paginated_response(PaymentSerializer(page, many=True).data)

    def post(self, request):
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        payment = PaymentService.create_payment(
            data['booking_id'],
            data['amount'],
            data['method'],
            request.user,
            request=request,
            bank_code=data.get('bank_code') or None,
            locale=data.get('locale', 'vn'),
        )
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(tags=[TAG_PAYMENTS], summary='Chi tiết thanh toán', responses={200: PaymentSerializer}),
)
class PaymentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        payment = get_object_or_404(PaymentService.get_payments_for_user(request.user), pk=pk)
        return Response(PaymentSerializer(payment).data)


@extend_schema_view(
    get=extend_schema(
        tags=[TAG_PAYMENTS],
        summary='VNPay IPN (callback server-to-server)',
        description='VNPay gọi GET với query params. Trả JSON thuần RspCode/Message (không bọc envelope).',
        parameters=[OpenApiParameter(name='vnp_TxnRef', type=str, location=OpenApiParameter.QUERY)],
        responses={200: {'description': 'JSON thuần: RspCode, Message'}},
        auth=[],
    ),
)
class VNPayIPNView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        valid, params = VNPayService.verify_return_params(request.GET)
        if not valid:
            return JsonResponse({'RspCode': '97', 'Message': 'Invalid Checksum'})
        result = PaymentService.process_vnpay_ipn(params)
        return JsonResponse(result)


@extend_schema_view(
    get=extend_schema(
        tags=[TAG_PAYMENTS],
        summary='VNPay Return URL (sau khi khách thanh toán)',
        description='Trình duyệt redirect về đây. Xác thực chữ ký và cập nhật payment.',
        responses={200: VNPayReturnSerializer},
        auth=[],
    ),
)
class VNPayReturnView(APIView):
    permission_classes = [AllowAny]

    @staticmethod
    def _build_html(success: bool, booking_id: str | None = None, booking_code: str | None = None, message: str | None = None) -> HttpResponse:
        data = {
            'success': success,
            'booking_id': booking_id,
            'booking_code': booking_code,
            'message': message or ('Thanh toán thành công!' if success else 'Thanh toán thất bại.'),
        }
        color = '#4CAF50' if success else '#E53935'
        icon = '✓' if success else '✗'
        title = 'Thanh toán thành công!' if success else 'Thanh toán thất bại'
        subtitle = 'Đang chuyển về ứng dụng...' if success else (message or 'Vui lòng thử lại trong ứng dụng.')
        spinner = '<div class="loader"></div>' if success else ''
        
        # Tạo query string cho web redirect
        query_string = f"?success={'1' if success else '0'}"
        if booking_id:
            query_string += f"&booking_id={booking_id}"
        if booking_code:
            query_string += f"&booking_code={booking_code}"
        if message:
            from urllib.parse import quote
            query_string += f"&message={quote(message)}"
        
        html = f"""<!DOCTYPE html>
<html lang="vi"><head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Kết quả thanh toán</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#1A1A2E;color:#fff;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:24px;text-align:center}}
    .card{{background:rgba(255,255,255,.06);border-radius:20px;padding:48px 32px;max-width:340px;width:100%}}
    .icon{{width:80px;height:80px;border-radius:50%;background:{color}22;border:2px solid {color};display:flex;align-items:center;justify-content:center;margin:0 auto 24px;font-size:36px;line-height:80px}}
    .title{{font-size:20px;font-weight:700;margin-bottom:8px;color:{color}}}
    .subtitle{{font-size:14px;color:#aaa;line-height:1.5;margin-bottom:20px}}
    .loader{{display:inline-block;width:24px;height:24px;border:3px solid rgba(255,255,255,.2);border-top-color:#C9A84C;border-radius:50%;animation:spin .8s linear infinite}}
    @keyframes spin{{to{{transform:rotate(360deg)}}}}
  </style>
</head><body>
  <div class="card">
    <div class="icon">{icon}</div>
    <div class="title">{title}</div>
    <div class="subtitle">{subtitle}</div>
    {spinner}
  </div>
  <script>
    var _d={json.dumps(data)};
    var isWebView = !!window.ReactNativeWebView;
    var isWeb = !isWebView;
    
    if(isWebView){{
      // Mobile WebView: gửi message về app
      window.ReactNativeWebView.postMessage(JSON.stringify(_d));
    }} else {{
      // Web Browser: redirect về frontend sau 2 giây
      setTimeout(function(){{
        var frontendUrl = window.location.origin.replace(':8000', ':5173');
        var redirectUrl = frontendUrl + '/payments/vnpay/return{query_string}';
        window.location.href = redirectUrl;
      }}, 2000);
    }}
  </script>
</body></html>"""
        return HttpResponse(html, content_type='text/html; charset=utf-8')

    def get(self, request):
        vnp_params = {key: value for key, value in request.GET.items() if key.startswith('vnp_')}

        valid, params = VNPayService.verify_return_params(vnp_params)
        if not valid:
            return self._build_html(False, message='Chữ ký không hợp lệ.')

        try:
            payment, vnp_params = PaymentService.process_vnpay_return(params)
            success = VNPayService.is_payment_success(vnp_params)
            booking_id = str(payment.booking_id)
            booking_code = str(payment.booking.booking_code)
            return self._build_html(success, booking_id=booking_id, booking_code=booking_code)
        except Exception as exc:
            return self._build_html(False, message=str(exc))


@extend_schema_view(
    post=extend_schema(
        tags=[TAG_PAYMENTS],
        summary='Webhook thanh toán thủ công (dev/MoMo)',
        request=PaymentWebhookSerializer,
        responses={200: PaymentSerializer},
        auth=[],
    ),
)
class PaymentWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PaymentWebhookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = PaymentService.complete_webhook(serializer.validated_data['transaction_ref'])
        return Response(PaymentSerializer(payment).data)


@extend_schema_view(
    post=extend_schema(tags=[TAG_PAYMENTS], summary='Hoàn tiền', request=PaymentRefundSerializer, responses={200: PaymentSerializer}),
)
class PaymentRefundView(APIView):
    permission_classes = [IsManager]

    def post(self, request, pk):
        payment = get_object_or_404(PaymentService.get_payments_for_user(request.user), pk=pk)
        serializer = PaymentRefundSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = PaymentService.refund(
            pk, serializer.validated_data['amount'], serializer.validated_data.get('reason', ''), request.user,
        )
        return Response(PaymentSerializer(payment).data)


@extend_schema_view(
    get=extend_schema(
        tags=[TAG_INVOICES],
        summary='Danh sách hóa đơn',
        parameters=[PARAM_PAGE, PARAM_PAGE_SIZE, OpenApiParameter(name='booking_id', type=str, location=OpenApiParameter.QUERY)],
        responses={200: InvoiceSerializer(many=True)},
    ),
)
class InvoiceListCreateView(APIView):
    permission_classes = [IsManagerOrReceptionist]

    def get(self, request):
        qs = Invoice.objects.select_related('booking').filter(is_active=True)
        booking_id = request.query_params.get('booking_id')
        if booking_id:
            qs = qs.filter(booking_id=booking_id)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs.order_by('-issued_at'), request)
        return paginator.get_paginated_response(InvoiceSerializer(page, many=True).data)


@extend_schema_view(
    get=extend_schema(tags=[TAG_INVOICES], summary='Chi tiết hóa đơn', responses={200: InvoiceSerializer}),
)
class InvoiceDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        invoice = get_object_or_404(Invoice.objects.select_related('booking'), pk=pk)
        if request.user.role == 'customer' and invoice.booking.customer_id != request.user.id:
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(InvoiceSerializer(invoice).data)




