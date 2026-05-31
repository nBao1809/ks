import hashlib
import hmac
import unicodedata
from decimal import Decimal
from datetime import timedelta
from urllib.parse import parse_qsl, quote_plus, urlencode, urlparse, urlunparse
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone

VN_TZ = ZoneInfo('Asia/Ho_Chi_Minh')


class VNPayService:
    VERSION = '2.1.0'
    COMMAND_PAY = 'pay'
    CURR_CODE = 'VND'
    ORDER_TYPE_HOTEL = 'other'

    @staticmethod
    def _config(name):
        return getattr(settings, name, '')

    @staticmethod
    def _now_local():
        return timezone.now().astimezone(VN_TZ)

    @staticmethod
    def txn_ref_from_payment_id(payment_id):
        return str(payment_id).replace('-', '')

    @staticmethod
    def payment_id_from_txn_ref(txn_ref):
        if len(txn_ref) == 32:
            return (
                f'{txn_ref[:8]}-{txn_ref[8:12]}-{txn_ref[12:16]}'
                f'-{txn_ref[16:20]}-{txn_ref[20:]}'
            )
        return txn_ref

    @staticmethod
    def sanitize_order_info(text):
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        allowed = []
        for ch in text:
            if ch.isalnum() or ch in ' .,-_':
                allowed.append(ch)
        return ' '.join(''.join(allowed).split())[:255] or 'Thanh toan dat phong'

    @staticmethod
    def _build_hash_data(params):
        pairs = []
        for key, val in sorted(params.items()):
            pairs.append(f'{quote_plus(str(key))}={quote_plus(str(val))}')
        return '&'.join(pairs)

    @staticmethod
    def hmac_sha512(data, secret):
        return hmac.new(
            secret.encode('utf-8'),
            data.encode('utf-8'),
            hashlib.sha512,
        ).hexdigest()

    @staticmethod
    def create_secure_hash(params, secret):
        return VNPayService.hmac_sha512(VNPayService._build_hash_data(params), secret)

    @staticmethod
    def verify_return_params(query_params):
        params = {k: v for k, v in query_params.items()}
        received_hash = params.pop('vnp_SecureHash', None)
        params.pop('vnp_SecureHashType', None)
        secret = VNPayService._config('VNPAY_HASH_SECRET')
        if not received_hash or not secret:
            return False, params
        calculated = VNPayService.create_secure_hash(params, secret)
        return hmac.compare_digest(calculated, received_hash), params

    @staticmethod
    def get_client_ip(request):
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded:
            return forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '127.0.0.1')

    @staticmethod
    def append_query_param(url, key, value):
        if not value:
            return url

        parsed = urlparse(url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query[key] = value
        return urlunparse(parsed._replace(query=urlencode(query)))

    @staticmethod
    def build_payment_url(payment, booking, request=None, bank_code=None, locale='vn', app_return_url=''):
        tmn_code = VNPayService._config('VNPAY_TMN_CODE')
        secret = VNPayService._config('VNPAY_HASH_SECRET')
        pay_url = VNPayService._config('VNPAY_PAY_URL')
        # Tự build return URL từ request host → không cần đổi .env khi IP thay đổi
        if request is not None:
            return_url = request.build_absolute_uri('/api/v1/payments/vnpay/return/')
        else:
            return_url = VNPayService._config('VNPAY_RETURN_URL')
        return_url = VNPayService.append_query_param(return_url, 'app_return_url', app_return_url)
        ip_addr = VNPayService.get_client_ip(request) if request else '127.0.0.1'

        txn_ref = VNPayService.txn_ref_from_payment_id(payment.id)
        amount_int = int(Decimal(payment.amount) * 100)
        now = VNPayService._now_local()
        create_date = now.strftime('%Y%m%d%H%M%S')
        expire_date = (now + timedelta(minutes=15)).strftime('%Y%m%d%H%M%S')
        order_info = VNPayService.sanitize_order_info(
            f'Thanh toan booking {booking.booking_code}',
        )

        params = {
            'vnp_Version': VNPayService.VERSION,
            'vnp_Command': VNPayService.COMMAND_PAY,
            'vnp_TmnCode': tmn_code,
            'vnp_Amount': str(amount_int),
            'vnp_CurrCode': VNPayService.CURR_CODE,
            'vnp_TxnRef': txn_ref,
            'vnp_OrderInfo': order_info,
            'vnp_OrderType': VNPayService.ORDER_TYPE_HOTEL,
            'vnp_Locale': locale,
            'vnp_ReturnUrl': return_url,
            'vnp_IpAddr': ip_addr,
            'vnp_CreateDate': create_date,
            'vnp_ExpireDate': expire_date,
        }
        if bank_code:
            params['vnp_BankCode'] = bank_code

        secure_hash = VNPayService.create_secure_hash(params, secret)
        query = urlencode(params)
        return f'{pay_url}?{query}&vnp_SecureHash={secure_hash}'

    @staticmethod
    def is_payment_success(vnp_params):
        return (
            str(vnp_params.get('vnp_ResponseCode', '')) == '00'
            and str(vnp_params.get('vnp_TransactionStatus', '')) == '00'
        )

    @staticmethod
    def vnp_amount_to_decimal(vnp_amount):
        return Decimal(str(vnp_amount)) / Decimal('100')
