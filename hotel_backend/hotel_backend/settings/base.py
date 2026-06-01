from pathlib import Path

import environ
import pymysql

pymysql.install_as_MySQLdb()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)

environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('DJANGO_SECRET_KEY', default='django-insecure-dev-only-change-in-production')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

# Auto-allow Render public hostname to avoid DisallowedHost on first deploy.
render_hostname = env('RENDER_EXTERNAL_HOSTNAME', default='').strip()
if render_hostname and render_hostname not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(render_hostname)

INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'cloudinary_storage',
    'django.contrib.staticfiles',
    'cloudinary',
    'corsheaders',
    'django_filters',
    'rest_framework',
    'oauth2_provider',
    'drf_spectacular',
    'channels',
    'app',
]

ASGI_APPLICATION = 'hotel_backend.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'app.core.middleware.AuditMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'hotel_backend.urls'
WSGI_APPLICATION = 'hotel_backend.wsgi.application'
ASGI_APPLICATION = 'hotel_backend.asgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': env('DB_NAME', default='hotel_db'),
        'USER': env('DB_USER', default='root'),
        'PASSWORD': env('DB_PASSWORD', default='1234'),
        'HOST': env('DB_HOST', default=''),
        'PORT': env('DB_PORT', default='3306'),
    },
}

AUTH_USER_MODEL = 'app.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Cloudinary - luu tru file media (avatar, anh phong, ...)
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': env('CLOUDINARY_CLOUD_NAME', default=''),
    'API_KEY': env('CLOUDINARY_API_KEY', default=''),
    'API_SECRET': env('CLOUDINARY_API_SECRET', default=''),
}
STORAGES = {
    'default': {
        'BACKEND': 'cloudinary_storage.storage.MediaCloudinaryStorage'
        if CLOUDINARY_STORAGE['CLOUD_NAME']
        else 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}

# Backward-compatible keys for packages that still read legacy Django settings names.
DEFAULT_FILE_STORAGE = STORAGES['default']['BACKEND']
STATICFILES_STORAGE = STORAGES['staticfiles']['BACKEND']

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])
CORS_ALLOW_ALL_ORIGINS = env.bool('CORS_ALLOW_ALL_ORIGINS', default=DEBUG)

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'oauth2_provider.contrib.rest_framework.OAuth2Authentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'app.core.pagination.StandardPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': (
        'app.core.renderers.EnvelopeJSONRenderer',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'app.core.exceptions.custom_exception_handler',
}

OAUTH2_PROVIDER = {
    'OAUTH2_BACKEND_CLASS': 'oauth2_provider.oauth2_backends.JSONOAuthLibCore',
    'ACCESS_TOKEN_EXPIRE_SECONDS': 3600,
    'SCOPES': {
        'read': 'Read access',
        'write': 'Write access',
    },
    'DEFAULT_SCOPES': ['read', 'write'],
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Smart Hotel API',
    'VERSION': '1.0.0',
    'DESCRIPTION': (
        'API quan ly khach san thong minh. '
        'Authorize bang OAuth2 password grant. '
        'Lay token tai /o/token/ (grant_type=password hoac refresh_token), '
        'thu hoi token tai /o/revoke_token/.'
    ),
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': r'/api/v1',
    'TAGS': [
        {'name': 'Auth', 'description': 'Dang ky, dang nhap, token, profile'},
        {'name': 'Staff', 'description': 'Quan ly nhan vien (Manager)'},
        {'name': 'Customers', 'description': 'Quan ly khach hang (Le tan/Manager)'},
        {'name': 'Room Types', 'description': 'Loai phong, anh, gia'},
        {'name': 'Rooms', 'description': 'Phong, trang thai, kiem tra trong'},
        {'name': 'Amenities', 'description': 'Tien nghi'},
        {'name': 'Bookings', 'description': 'Dat phong, check-in/out'},
        {'name': 'Payments', 'description': 'Thanh toan'},
        {'name': 'Invoices', 'description': 'Hoa don'},
        {'name': 'Hotel Services', 'description': 'Spa, nha hang, dua don'},
        {'name': 'Housekeeping', 'description': 'Don phong'},
        {'name': 'Notifications', 'description': 'Thong bao in-app'},
        {'name': 'Analytics', 'description': 'Bao cao, dashboard (Manager)'},
        {'name': 'Health', 'description': 'Health check'},
    ],
    'APPEND_COMPONENTS': {
        'securitySchemes': {
            'OAuth2Password': {
                'type': 'oauth2',
                'flows': {
                    'password': {
                        'tokenUrl': '/o/token/',
                        'scopes': {
                            'read': 'Read access',
                            'write': 'Write access',
                        },
                    },
                },
                'description': 'OAuth2 password grant. Lay token tai /o/token/.',
            },
            'BearerAuth': {
                'type': 'http',
                'scheme': 'bearer',
                'description': 'Dan access_token thu cong de goi API.',
            },
        },
    },
    'SECURITY': [
        {'OAuth2Password': ['read', 'write']},
        {'BearerAuth': []},
    ],
    'SWAGGER_UI_SETTINGS': {
        'persistAuthorization': True,
        'displayRequestDuration': True,
        'filter': True,
    },
    # 'SWAGGER_UI_OAUTH2_CONFIG': {
    #     'clientId': SWAGGER_OAUTH_CLIENT_ID,
    #     'clientSecret': SWAGGER_OAUTH_CLIENT_SECRET,
    #     'scopes': 'read write',
    # },
}

EMAIL_BACKEND = env(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.console.EmailBackend',
)
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='Smart Hotel <noreply@smarthotel.vn>')

BACKEND_BASE_URL = env('BACKEND_BASE_URL', default='http://127.0.0.1:8000')
VNPAY_TMN_CODE = env('VNPAY_TMN_CODE', default='')
VNPAY_HASH_SECRET = env('VNPAY_HASH_SECRET', default='')
VNPAY_PAY_URL = env(
    'VNPAY_PAY_URL',
    default='https://sandbox.vnpayment.vn/paymentv2/vpcpay.html',
)
VNPAY_RETURN_URL = env(
    'VNPAY_RETURN_URL',
    default=f'{BACKEND_BASE_URL}/api/v1/payments/vnpay/return/',
)
VNPAY_IPN_URL = env(
    'VNPAY_IPN_URL',
    default=f'{BACKEND_BASE_URL}/api/v1/payments/vnpay/ipn/',
)
