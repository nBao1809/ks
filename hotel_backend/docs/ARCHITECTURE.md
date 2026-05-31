# Smart Hotel Management System — Backend Architecture

## 1. Tổng quan

| Thành phần | Công nghệ |
|------------|-----------|
| Framework | Django 5.x + Django REST Framework 3.15+ |
| Database | PostgreSQL 16+ |
| Auth | OAuth2 (django-oauth-toolkit) + JWT (djangorestframework-simplejwt) |
| File storage | S3-compatible / local (django-storages) |
| Cache | Redis |
| Task queue | Celery + Redis |
| API docs | drf-spectacular (OpenAPI 3) |
| Admin | Django Admin (Super Admin) |

### Luồng client

```
┌─────────────┐     ┌─────────────┐     ┌──────────────────┐
│ Mobile App  │     │ Web React   │     │ Django Admin     │
│ Customer +  │     │ Manager +   │     │ Super Admin      │
│ Housekeeping│     │ Receptionist│     │                  │
└──────┬──────┘     └──────┬──────┘     └────────┬─────────┘
       │                   │                      │
       └───────────────────┼──────────────────────┘
                           ▼
              ┌────────────────────────┐
              │  API Gateway (Nginx)     │
              │  /api/v1/                │
              └────────────┬───────────┘
                           ▼
              ┌────────────────────────┐
              │  Django + DRF          │
              │  Service Layer         │
              │  Permission Layer      │
              └────────────┬───────────┘
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
   PostgreSQL           Redis            Celery Workers
                                              │
                                         Email / Push
```

---

## 2. Cấu trúc thư mục

```
smart-hotel-backend/
├── config/
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── development.py
│   │   ├── production.py
│   │   └── test.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── core/
│   │   ├── models.py              # BaseModel, mixins
│   │   ├── exceptions.py          # Custom API exceptions
│   │   ├── pagination.py
│   │   ├── permissions.py         # Base permission classes
│   │   ├── renderers.py
│   │   ├── filters.py
│   │   ├── middleware.py          # Request ID, audit
│   │   └── utils.py
│   ├── accounts/
│   │   ├── models.py              # User, Role, Profile
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── services/
│   │   ├── permissions.py
│   │   └── urls.py
│   ├── rooms/
│   ├── bookings/
│   ├── payments/
│   ├── services/                  # Hotel services (spa, restaurant...)
│   ├── housekeeping/
│   ├── notifications/
│   └── analytics/
├── manage.py
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
├── API.md
└── docs/
    ├── ARCHITECTURE.md
    ├── DATABASE.md
    ├── PERMISSIONS.md
    └── IMPLEMENTATION.md
```

### Nguyên tắc tổ chức mỗi app

```
apps/<app_name>/
├── models.py
├── admin.py
├── serializers/
│   ├── __init__.py
│   ├── read.py
│   └── write.py
├── views/
│   ├── __init__.py
│   └── v1.py
├── services/
│   ├── __init__.py
│   └── <domain>_service.py
├── permissions.py
├── filters.py
├── urls.py
├── signals.py
├── tasks.py
└── tests/
```

**View** chỉ validate input, gọi **Service**, trả **Serializer**.  
**Service** chứa business logic, transaction, gọi model/repository.  
**Model** chỉ data + constraints, không logic phức tạp.

---

## 3. Danh sách Django apps

| App | Trách nhiệm |
|-----|-------------|
| `core` | BaseModel, exception handler, pagination, shared filters, health check |
| `accounts` | User, Role, RBAC, register/login, password reset, profile |
| `rooms` | RoomType, Room, Image, Amenity, Price, status |
| `bookings` | Booking, BookingRoom, availability, check-in/out, special request |
| `payments` | Payment, Invoice, Transaction, refund |
| `services` | ServiceCategory, Service, ServiceOrder, usage history |
| `housekeeping` | HousekeepingTask, assignment, room cleaning status |
| `notifications` | Notification template, queue, email log |
| `analytics` | Revenue, occupancy, reports (read-only aggregates) |

**Không tách app theo role** — phân quyền bằng permission class + role trên User.

---

## 4. Authentication strategy

### OAuth2 + JWT (khuyến nghị production)

| Token | Mục đích | Thời gian |
|-------|----------|-----------|
| Access (JWT) | Bearer header mọi API | 15 phút |
| Refresh (JWT) | `/auth/token/refresh/` | 7 ngày |
| OAuth2 Application | Đăng ký client mobile/web | — |

**Luồng đăng nhập**

1. Client gửi `username` + `password` (+ `client_id` nếu OAuth2 password grant cho dev).
2. Server trả `access`, `refresh`, `user` (role, permissions summary).
3. Mọi request: `Authorization: Bearer <access>`.
4. Hết hạn → refresh → logout blacklist refresh token.

**Đăng ký Customer**: public endpoint, role mặc định `customer`.  
**Staff** (manager, receptionist, housekeeping): chỉ Manager/Super Admin tạo qua API hoặc Admin.

---

## 5. Service layer pattern

```python
class BookingService:
    @staticmethod
    @transaction.atomic
    def create_booking(user, data):
        BookingValidator.validate_availability(data)
        booking = Booking.objects.create(...)
        RoomService.reserve_rooms(booking)
        NotificationService.send_booking_confirmation(booking)
        return booking
```

- Một use-case = một method service.
- `@transaction.atomic` cho thao tác đa bảng.
- Raise `core.exceptions.BusinessException` → global handler trả JSON chuẩn.

### Exception response format

```json
{
  "success": false,
  "error": {
    "code": "ROOM_NOT_AVAILABLE",
    "message": "Phòng không còn trống trong khoảng thời gian đã chọn",
    "details": {}
  }
}
```

---

## 6. API conventions

| Quy ước | Giá trị |
|---------|---------|
| Base URL | `/api/v1/` |
| Versioning | URL prefix `v1` |
| Pagination | `?page=1&page_size=20` (max 100) |
| Filtering | `django-filter` |
| Search | `?search=` trên ViewSet có `search_fields` |
| Ordering | `?ordering=-created_at` |
| ID format | UUID v4 (khuyến nghị) hoặc BigInt |
| Datetime | ISO 8601 UTC `2026-05-21T10:00:00Z` |
| Money | Decimal string `"1500000.00"`, currency `VND` |

---

## 7. Cross-cutting concerns

### BaseModel (mọi entity nghiệp vụ)

| Field | Type |
|-------|------|
| id | UUID PK |
| is_active | Boolean, default True |
| created_at | DateTime auto |
| updated_at | DateTime auto |
| created_by | FK User, null, SET_NULL |

### Audit middleware

Gắn `request.user` vào thread-local; signal `pre_save` set `created_by` nếu null.

### Image upload

- Endpoint riêng hoặc nested trong Room/User.
- Validate: jpg/png/webp, max 5MB.
- Lưu qua `django-storages` → S3 path `rooms/{id}/{uuid}.jpg`.

### Swagger

- `/api/schema/` — OpenAPI YAML
- `/api/docs/` — Swagger UI
- Phân tag theo app.

### Celery tasks

- Gửi email xác nhận booking
- Payment notification
- Room ready notification
- Báo cáo tháng (pre-aggregate)

---

## 8. Scalability & production

| Hạng mục | Giải pháp |
|----------|-----------|
| DB | PostgreSQL, index trên `booking(check_in, check_out, status)`, `room(status)` |
| Read heavy reports | Materialized view hoặc bảng `analytics_daily_snapshot` |
| Concurrency booking | `select_for_update()` khi giữ phòng |
| Rate limit | django-ratelimit / throttling DRF theo role |
| Secrets | `.env` — không commit |
| Deploy | Gunicorn + Nginx, `DEBUG=False`, `ALLOWED_HOSTS` cụ thể |
| Migrations | Squash định kỳ, zero-downtime với `SeparateDatabaseAndState` khi cần |

---

## 9. Environment variables

```
DJANGO_SECRET_KEY=
DATABASE_URL=postgres://user:pass@localhost:5432/smart_hotel
REDIS_URL=redis://localhost:6379/0
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_STORAGE_BUCKET_NAME=
EMAIL_HOST=
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
JWT_ACCESS_MINUTES=15
JWT_REFRESH_DAYS=7
CORS_ALLOWED_ORIGINS=
```

---

## 10. Health & monitoring

| Endpoint | Auth | Mô tả |
|----------|------|-------|
| `GET /api/v1/health/` | Public | DB + Redis ping |
| `GET /api/v1/health/ready/` | Public | Migration ready |

Logging: JSON structured, `request_id` correlation.
