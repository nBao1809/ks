from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler


class BusinessException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'BUSINESS_ERROR'

    def __init__(self, message, code=None, details=None, status_code=None):
        self.detail = {
            'code': code or self.default_code,
            'message': message,
            'details': details or {},
        }
        if status_code:
            self.status_code = status_code


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response

    if isinstance(exc, BusinessException):
        data = exc.detail
    elif isinstance(response.data, dict) and 'detail' in response.data:
        data = {
            'code': 'ERROR',
            'message': str(response.data['detail']),
            'details': {k: v for k, v in response.data.items() if k != 'detail'},
        }
    else:
        data = {
            'code': 'VALIDATION_ERROR',
            'message': 'Dữ liệu không hợp lệ',
            'details': response.data,
        }

    response.data = {
        'success': False,
        'error': data,
    }
    return response
