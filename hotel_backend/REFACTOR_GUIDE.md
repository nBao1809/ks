# TÀI LIỆU HƯỚNG DẪN REFACTOR CẤU TRÚC CODE (MULTI-APP SANG SINGLE-APP)

## 🎯 VAI TRÒ CỦA AI:
Bạn đóng vai trò là một Chuyên gia Kỹ thuật/AI Developer. Nhiệm vụ của bạn là thực hiện refactor cấu trúc thư mục của dự án `smart-hotel-backend` từ dạng **multi-app** (nhiều app nhỏ nằm trong thư mục `apps/`) sang dạng **single-app** (chỉ còn một app duy nhất nằm ngay tại thư mục gốc tên là `app/`).

### ⚠️ NGUYÊN TẮC BẮT BUỘC (QUAN TRỌNG TỐI CAO):
1. **KHÔNG THAY ĐỔI LOGIC CODE:** Giữ nguyên toàn bộ logic xử lý, hàm, class bên trong. Chỉ di chuyển file, gộp file và điều chỉnh lại các đường dẫn `import` cho đúng cấu trúc mới.
2. **GOM CHUNG THÀNH FILE ĐƠN LẺ:** Đối với các thành phần độc lập (`models`, `permissions`, `urls`, `admins`), bạn phải gộp toàn bộ code của các module cũ vào **duy nhất 1 file** (Ví dụ: Tất cả model nằm chung trong file `app/models.py`).
3. **TẠO THƯ MỤC CON CHO MODULE PHỨC TẠP:** Đối với `views` và `serializers`, bạn phải tạo một thư mục chung, bên trong chia thành các thư mục con theo tên module cũ (Ví dụ: `app/views/accounts/views.py`).
4. **HỦY BỎ MIGRATIONS CŨ:** Toàn bộ lịch sử và các file migrations cũ của các app rải rác sẽ **bị xóa bỏ hoàn toàn (không cần giữ)**. Hệ thống cơ sở dữ liệu sẽ được tạo lại bằng một file migration khởi tạo duy nhất cho app `app/` mới.
5. **QUY TRÌNH CUỐN CHIẾU (STEP-BY-STEP):** Bạn phải thực hiện **TỪNG BƯỚC MỘT** theo đúng thứ tự dưới đây. Cuối mỗi bước, bạn **BẮT BUỘC PHẢI DỪNG LẠI**, cập nhật bảng Checklist tiến độ, xuất toàn bộ code đã xử lý và đợi User viết câu lệnh: *"Đã duyệt bước X, tiếp tục"* thì mới được làm bước tiếp theo.
6. **DỌN FILE THỪA SAU MỖI BƯỚC ĐƯỢC DUYỆT:** Ngay sau khi User xác nhận duyệt xong một bước, trước khi làm bước kế tiếp phải xóa toàn bộ file cũ đã được chuyển/gộp thành công ở bước vừa duyệt (tránh trùng lặp source), đồng thời báo rõ danh sách file đã xóa.

---

## 📊 BẢNG CHECKLIST TIẾN ĐỘ REFACTOR
*(AI có nhiệm vụ cập nhật trạng thái `[ ]` thành `[x]` của từng bước trước khi xuất code dừng chờ duyệt)*

- [x] **Bước 1:** Khởi tạo app `app/`, gộp toàn bộ Models và xóa sạch Migrations cũ.
- [x] **Bước 2:** Gộp file Permissions và Admins hệ thống.
- [x] **Bước 3:** Di chuyển và tổ chức lại cấu trúc thư mục `serializers/`.
- [x] **Bước 4:** Di chuyển và tổ chức lại cấu trúc thư mục `views/` & `services/`.
- [x] **Bước 5:** Gộp định tuyến `urls.py` và cập nhật cấu hình `config/` toàn hệ thống.

---

## 📂 CẤU TRÚC MỤC TIÊU SẼ ĐẠT ĐƯỢC
```text
smart-hotel-backend/
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── ...
│   ├── urls.py
│   └── ...
├── app/                      # Ứng dụng Single-App duy nhất tại thư mục gốc
│   ├── __init__.py
│   ├── apps.py                 # Khai báo AppConfig cho 'app'
│   ├── migrations/             # Thư mục migrations mới (Chỉ chứa file khởi tạo sau khi làm xong)
│   │   └── __init__.py
│   │
│   │── # --- CÁC FILE ĐƠN LẺ GỘP CHUNG TOÀN HỆ THỐNG ---
│   ├── models.py               # Gom toàn bộ model (User, Room, Booking...)
│   ├── permissions.py          # Gom toàn bộ class permission 
│   ├── urls.py                 # Gom toàn bộ tuyến đường API nội bộ của app
│   ├── admins.py               # Gom toàn bộ cấu hình Django Admin
│   │
│   │── # --- CÁC THƯ MỤC PHỨC TẠP (CHỨA THƯ MỤC CON) ---
│   ├── views/
│   │   ├── accounts/
│   │   │   └── views.py
│   │   ├── bookings/
│   │   │   └── views.py
│   │   └── ... (rooms, payments, services, housekeeping, notifications, analytics)
│   ├── serializers/
│   │   ├── accounts/
│   │   │   └── serializers.py
│   │   ├── bookings/
│   │   │   └── serializers.py
│   │   └── ...
│   │
│   │── # --- CÁC THÀNH PHẦN KẾ THỪA TỪ CORE CŨ ---
│   ├── middleware.py
│   ├── utils.py
│   ├── pagination.py
│   ├── renderers.py
│   └── filters.py
│   └── exceptions.py
├── manage.py
└── ...
🛠️ LỘ TRÌNH THỰC HIỆN CHI TIẾT
📌 BƯỚC 1: KHỞI TẠO APP, GỘP TOÀN BỘ MODELS VÀ XÓA MIGRATIONS CŨ
Công việc AI cần làm:

Tạo cấu hình app mới trong file app/apps.py (Khai báo class AppConfig, thiết lập name = 'app').

Khởi tạo thư mục app/migrations/ mới và chỉ để lại duy nhất một file __init__.py trống bên trong. Loại bỏ/Xóa bỏ hoàn toàn tất cả các thư mục và file migrations/ cũ ở các app trong apps/ cũ (Không giữ lại bất kỳ file migration cũ nào).

Thu thập toàn bộ nội dung từ file models.py của core và tất cả các app cũ bao gồm cả file constants.py (accounts, rooms, bookings, payments, services, housekeeping, notifications, analytics).

Gộp tất cả vào file duy nhất app/models.py.

Quy tắc xếp code: Đặt BaseModel và các mixin lên trên cùng, tiếp theo là các model độc lập, cuối cùng là các model chứa khóa ngoại (ForeignKey, OneToOneField) để tránh lỗi biên dịch của Python khi đọc file từ trên xuống.

Sửa Import: Xóa bỏ các dòng import model lẫn nhau giữa các app cũ vì giờ tất cả đã ở chung một file.

Di chuyển các file bổ trợ từ apps/core/ sang thư mục app/ bao gồm: exceptions.py, pagination.py, renderers.py, filters.py, middleware.py, utils.py.

🛑 YÊU CẦU DỪNG: Cập nhật bảng Checklist tiến độ. Xuất toàn bộ mã nguồn của file app/apps.py và app/models.py sau khi gộp. DỪNG LẠI và đợi User review.

📌 BƯỚC 2: GỘP FILE PERMISSIONS VÀ ADMINS
(Chỉ thực hiện khi User đã duyệt Bước 1)

Công việc AI cần làm:

Khởi tạo file app/permissions.py. Thu thập toàn bộ class phân quyền từ apps/core/permissions.py, apps/accounts/permissions.py và các app khác, gộp nối tiếp nhau vào file này.

Khởi tạo file app/admins.py. Gom toàn bộ cấu hình admin.site.register từ tất cả các file admin.py của các app cũ vào đây.

Sửa lại các đường dẫn import mô hình bên trong 2 file này thành: from app.models import <Tên_Model>.

🛑 YÊU CẦU DỪNG: Cập nhật bảng Checklist tiến độ. Xuất nội dung hoàn chỉnh của app/permissions.py và app/admins.py. DỪNG LẠI và đợi User review.

📌 BƯỚC 3: DI CHUYỂN VÀ TỔ CHỨC LẠI THƯ MỤC SERIALIZERS
(Chỉ thực hiện khi User đã duyệt Bước 2)

Công việc AI cần làm:

Tạo thư mục app/serializers/.

Tạo các thư mục con bên trong tương ứng với từng module cũ (Ví dụ: app/serializers/accounts/, app/serializers/bookings/, ...).

Đặt các file serializers.py cũ vào đúng thư mục con tương ứng.

Sửa lại Import nội bộ: * Sửa các dòng import model thành: from app.models import <Tên_Model>.

Sửa các dòng import serializer chéo giữa các module (nếu có) theo cấu trúc mới: from app.serializers.<tên_module>.serializers import <Tên_Serializer>.

🛑 YÊU CẦU DỪNG: Cập nhật bảng Checklist tiến độ. Hiển thị cấu trúc thư mục app/serializers/ và xuất mã nguồn minh họa của ít nhất 2 file serializer chính (như accounts và bookings) đã được sửa import. DỪNG LẠI và đợi User review.

📌 BƯỚC 4: DI CHUYỂN VÀ TỔ CHỨC LẠI THƯ MỤC VIEWS & SERVICES
(Chỉ thực hiện khi User đã duyệt Bước 3)

Công việc AI cần làm:

Tạo thư mục app/views/. Chia các thư mục con bên trong: app/views/accounts/, app/views/bookings/,... và đưa file views.py tương ứng vào.

Nếu các app cũ có thư mục services/ (Ví dụ: apps/accounts/services/), hãy di chuyển chúng thành thư mục con nằm trong views hoặc song song trong module đó (Ví dụ: app/views/accounts/services/).

Cập nhật lại toàn bộ Import: Sửa đường dẫn import của models, serializers, permissions, pagination, exceptions trong tất cả các file views sang cấu trúc đơn lẻ mới (app.models, app.permissions, v.v.).

🛑 YÊU CẦU DỪNG: Cập nhật bảng Checklist tiến độ. Xuất mã nguồn hoàn chỉnh của file app/views/accounts/views.py đã được refactor sạch sẽ phần import để User kiểm tra mẫu. DỪNG LẠI và đợi User review.

📌 BƯỚC 5: GỘP URLS VÀ CẬP NHẬT CẤU HÌNH CONFIG TOÀN HỆ THỐNG
(Chỉ thực hiện khi User đã duyệt Bước 4)

Công việc AI cần làm:

Khởi tạo file app/urls.py duy nhất cho toàn bộ app app.

Gộp tất cả các urlpatterns từ các app cũ vào file này. Bạn cần đổi tên hoặc phân nhóm bằng path('accounts/', ...) hoặc gom chung lại một cách tường minh để thay thế cho việc include() nhiều app cũ.

Cập nhật file cấu hình gốc config/settings/base.py:

Trong danh sách INSTALLED_APPS: Xóa bỏ tất cả các app cũ (apps.accounts, apps.rooms...) và thêm vào app duy nhất: 'app'.

Cập nhật file định tuyến gốc config/urls.py:

Thay đổi dòng include cũ dẫn đến các app con thành một dòng duy nhất dẫn đến app mới: path('api/', include('app.urls')).

🛑 YÊU CẦU DỪNG: Cập nhật bảng Checklist tiến độ (hoàn thành 100%). Xuất toàn bộ mã nguồn file app/urls.py mới, file config/urls.py và đoạn code thay đổi trong base.py. Đợi User kiểm duyệt bước cuối cùng để hoàn tất quá trình refactor.