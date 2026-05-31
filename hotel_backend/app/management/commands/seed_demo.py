from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from app.models import UserRole
from app.models import StaffProfile, User
from app.models import Booking, BookingRoom, BookingStatus
from app.models import HousekeepingTask, TaskPriority, TaskStatus, TaskType
from app.models import Notification, NotificationChannel, NotificationType
from app.models import Payment, PaymentMethod, PaymentStatus
from app.models import Amenity, Room, RoomPrice, RoomStatus, RoomType, RoomTypeImage
from app.models import Service, ServiceCategory


class Command(BaseCommand):
    help = "Seed demo data"

    @transaction.atomic
    def handle(self, *args, **options):
        users = self._seed_users()
        amenities = self._seed_amenities()
        room_types = self._seed_room_types(amenities)
        self._seed_room_type_images(room_types)
        rooms = self._seed_rooms(room_types)
        bookings = self._seed_bookings(users, rooms, room_types)
        self._seed_services()
        self._seed_notifications(users, bookings)
        self._seed_payments(bookings)
        self._seed_housekeeping_tasks(users, rooms)
        self._print_amenity_icon_guide()
        self.stdout.write(self.style.SUCCESS("Seed completed. Password: Admin@123"))

    def _ensure_password(self, user, raw_password):
        user.set_password(raw_password)
        user.save(update_fields=["password"])

    def _seed_users(self):
        admin, created = User.objects.get_or_create(
            email="admin@hotel.com",
            defaults={
                "username": "admin@hotel.com",
                "full_name": "Super Admin",
                "role": UserRole.MANAGER,
                "is_superuser": True,
                "is_staff": True,
                "email_verified": True,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS("Admin: admin@hotel.com / Admin@123"))
        admin.is_superuser = True
        admin.is_staff = True
        admin.role = UserRole.MANAGER
        admin.save(update_fields=["is_superuser", "is_staff", "role"])
        self._ensure_password(admin, "Admin@123")

        manager, _ = User.objects.update_or_create(
            email="manager@hotel.com",
            defaults={
                "username": "manager@hotel.com",
                "full_name": "Hotel Manager",
                "role": UserRole.MANAGER,
                "is_staff": True,
                "email_verified": True,
            },
        )
        self._ensure_password(manager, "Admin@123")
        StaffProfile.objects.update_or_create(
            user=manager,
            defaults={"employee_code": "MGR-001", "department": "Management", "hire_date": date(2023, 1, 2)},
        )

        reception, _ = User.objects.update_or_create(
            email="reception@hotel.com",
            defaults={
                "username": "reception@hotel.com",
                "full_name": "Le Tan",
                "role": UserRole.RECEPTIONIST,
                "is_staff": True,
                "email_verified": True,
            },
        )
        self._ensure_password(reception, "Admin@123")
        StaffProfile.objects.update_or_create(
            user=reception,
            defaults={"employee_code": "REC-001", "department": "Front Desk", "hire_date": date(2023, 3, 1)},
        )

        housekeeping, _ = User.objects.update_or_create(
            email="housekeeping@hotel.com",
            defaults={
                "username": "housekeeping@hotel.com",
                "full_name": "Nhan Vien Don Phong",
                "role": UserRole.HOUSEKEEPING,
                "is_staff": True,
                "email_verified": True,
            },
        )
        self._ensure_password(housekeeping, "Admin@123")
        StaffProfile.objects.update_or_create(
            user=housekeeping,
            defaults={"employee_code": "HK-001", "department": "Housekeeping", "hire_date": date(2023, 4, 1)},
        )

        customer, _ = User.objects.update_or_create(
            email="customer@hotel.com",
            defaults={
                "username": "customer@hotel.com",
                "full_name": "Khach Hang Demo",
                "role": UserRole.CUSTOMER,
                "email_verified": True,
            },
        )
        self._ensure_password(customer, "Admin@123")
        return {
            "admin": admin,
            "manager": manager,
            "reception": reception,
            "housekeeping": housekeeping,
            "customer": customer,
        }

    def _seed_amenities(self):
        amenity_data = [
            ("WiFi", "wifi"),
            ("Air Conditioner", "air-conditioner"),
            ("TV", "television"),
            ("Minibar", "fridge-outline"),
            ("Bathtub", "bathtub-outline"),
            ("Shower", "shower"),
            ("Safe Box", "safe"),
            ("Balcony", "balcony"),
            ("Living Room", "sofa-outline"),
            ("Work Desk", "desk"),
            ("Coffee Maker", "coffee-maker-outline"),
            ("City View", "city-variant-outline"),
            ("Sea View", "image-filter-hdr"),
            ("King Bed", "bed-king-outline"),
            ("Breakfast", "food-croissant"),
        ]
        out = {}
        for name, icon in amenity_data:
            out[name], _ = Amenity.objects.update_or_create(name=name, defaults={"icon": icon})
        return out

    def _seed_room_types(self, amenities):
        room_type_data = {
            "Standard": {
                "description": "Standard room with essential amenities.",
                "max_occupancy": 2,
                "base_price": Decimal("800000.00"),
                "amenities": ["WiFi", "Air Conditioner", "TV", "Shower", "Work Desk"],
            },
            "Deluxe": {
                "description": "Spacious deluxe room with balcony.",
                "max_occupancy": 2,
                "base_price": Decimal("1400000.00"),
                "amenities": [
                    "WiFi",
                    "Air Conditioner",
                    "TV",
                    "Minibar",
                    "Shower",
                    "Balcony",
                    "City View",
                    "Breakfast",
                ],
            },
            "Suite": {
                "description": "Luxury suite with living space.",
                "max_occupancy": 3,
                "base_price": Decimal("3200000.00"),
                "amenities": [
                    "WiFi",
                    "Air Conditioner",
                    "TV",
                    "Minibar",
                    "Bathtub",
                    "Shower",
                    "Safe Box",
                    "Balcony",
                    "Living Room",
                    "Coffee Maker",
                    "Sea View",
                    "King Bed",
                ],
            },
            "Family": {
                "description": "Large family room for groups.",
                "max_occupancy": 4,
                "base_price": Decimal("2100000.00"),
                "amenities": [
                    "WiFi",
                    "Air Conditioner",
                    "TV",
                    "Minibar",
                    "Shower",
                    "Living Room",
                    "Work Desk",
                    "Breakfast",
                ],
            },
            "Premier": {
                "description": "Premium room with king bed and skyline view.",
                "max_occupancy": 3,
                "base_price": Decimal("1800000.00"),
                "amenities": [
                    "WiFi",
                    "Air Conditioner",
                    "TV",
                    "Minibar",
                    "Shower",
                    "City View",
                    "King Bed",
                    "Coffee Maker",
                    "Breakfast",
                ],
            },
        }

        out = {}
        for name, cfg in room_type_data.items():
            room_type, _ = RoomType.objects.update_or_create(
                name=name,
                defaults={
                    "description": cfg["description"],
                    "max_occupancy": cfg["max_occupancy"],
                    "base_price": cfg["base_price"],
                },
            )
            room_type.amenities.set([amenities[x] for x in cfg["amenities"]])
            RoomPrice.objects.update_or_create(
                room_type=room_type,
                valid_from=date(2025, 1, 1),
                valid_to=None,
                defaults={"price": cfg["base_price"]},
            )
            out[name] = room_type
        return out

    def _seed_room_type_images(self, room_types):
        cloudinary_pool = [
            "https://res.cloudinary.com/dblzpkokm/image/upload/v1779632953/deluxe-triple_hnrhov.jpg",
            "https://res.cloudinary.com/dblzpkokm/image/upload/v1779632948/hotel2_dvddsz.jpg",
            "https://res.cloudinary.com/dblzpkokm/image/upload/v1779632942/hotel1_utrbss.webp",
        ]

        room_type_images = {
            "Deluxe": [cloudinary_pool[0], cloudinary_pool[1], cloudinary_pool[2]],
            "Standard": [cloudinary_pool[1], cloudinary_pool[2]],
            "Suite": [cloudinary_pool[2], cloudinary_pool[0]],
            "Family": [cloudinary_pool[0], cloudinary_pool[1]],
            "Premier": [cloudinary_pool[1], cloudinary_pool[0]],
        }

        for room_type_name, image_urls in room_type_images.items():
            room_type = room_types.get(room_type_name)
            if not room_type:
                continue

            RoomTypeImage.objects.filter(room_type=room_type).delete()

            for idx, image_url in enumerate(image_urls):
                try:
                    request = Request(image_url, headers={"User-Agent": "Mozilla/5.0"})
                    with urlopen(request, timeout=20) as response:
                        content = response.read()

                    parsed = urlparse(image_url)
                    ext = Path(parsed.path).suffix or ".jpg"
                    filename = f"{room_type_name.lower()}-{idx + 1}{ext}"

                    image_obj = RoomTypeImage(
                        room_type=room_type,
                        is_primary=(idx == 0),
                        sort_order=idx,
                    )
                    image_obj.image.save(filename, ContentFile(content), save=True)
                except Exception as exc:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skip image for {room_type_name}: {image_url} -> {exc}"
                        )
                    )

    def _print_amenity_icon_guide(self):
        self.stdout.write("Amenity icon guide (MaterialCommunityIcons):")
        for amenity in Amenity.objects.order_by("name"):
            self.stdout.write(f"- {amenity.name}: {amenity.icon}")

    def _seed_rooms(self, room_types):
        room_data = [
            ("101", 1, "Standard", RoomStatus.AVAILABLE, ""),
            ("102", 1, "Standard", RoomStatus.OCCUPIED, ""),
            ("103", 1, "Standard", RoomStatus.CLEANING, ""),
            ("201", 2, "Deluxe", RoomStatus.AVAILABLE, ""),
            ("202", 2, "Deluxe", RoomStatus.RESERVED, ""),
            ("301", 3, "Suite", RoomStatus.AVAILABLE, "VIP floor"),
            ("302", 3, "Suite", RoomStatus.MAINTENANCE, "AC issue"),
            ("401", 4, "Family", RoomStatus.AVAILABLE, ""),
            ("402", 4, "Family", RoomStatus.OCCUPIED, ""),
            ("501", 5, "Premier", RoomStatus.AVAILABLE, ""),
            ("502", 5, "Premier", RoomStatus.AVAILABLE, "New wing"),
        ]
        out = {}
        for room_number, floor, room_type_name, status, notes in room_data:
            room, _ = Room.objects.update_or_create(
                room_number=room_number,
                defaults={
                    "floor": floor,
                    "room_type": room_types[room_type_name],
                    "status": status,
                    "notes": notes,
                },
            )
            out[room_number] = room
        return out

    def _seed_bookings(self, users, rooms, room_types):
        booking_defs = [
            {
                "booking_code": "BK20260001",
                "status": BookingStatus.CONFIRMED,
                "check_in": date(2026, 5, 26),
                "check_out": date(2026, 5, 28),
                "adults": 2,
                "children": 0,
                "total": Decimal("2800000.00"),
                "special_request": "High floor if available.",
                "room": "201",
                "room_type": "Deluxe",
                "ppn": Decimal("1400000.00"),
                "nights": 2,
            },
            {
                "booking_code": "BK20260002",
                "status": BookingStatus.PENDING,
                "check_in": date(2026, 6, 10),
                "check_out": date(2026, 6, 12),
                "adults": 2,
                "children": 1,
                "total": Decimal("6400000.00"),
                "special_request": "",
                "room": "301",
                "room_type": "Suite",
                "ppn": Decimal("3200000.00"),
                "nights": 2,
            },
            {
                "booking_code": "BK20260003",
                "status": BookingStatus.CHECKED_IN,
                "check_in": date(2026, 5, 24),
                "check_out": date(2026, 5, 25),
                "adults": 2,
                "children": 0,
                "total": Decimal("800000.00"),
                "special_request": "Need baby crib.",
                "checked_in_at": timezone.make_aware(datetime(2026, 5, 24, 14, 0, 0)),
                "room": "102",
                "room_type": "Standard",
                "ppn": Decimal("800000.00"),
                "nights": 1,
            },
        ]

        out = {}
        for item in booking_defs:
            booking, _ = Booking.objects.update_or_create(
                booking_code=item["booking_code"],
                defaults={
                    "customer": users["customer"],
                    "status": item["status"],
                    "check_in_date": item["check_in"],
                    "check_out_date": item["check_out"],
                    "adults": item["adults"],
                    "children": item["children"],
                    "total_amount": item["total"],
                    "special_request": item["special_request"],
                    "checked_in_at": item.get("checked_in_at"),
                },
            )
            BookingRoom.objects.update_or_create(
                booking=booking,
                room=rooms[item["room"]],
                defaults={
                    "room_type": room_types[item["room_type"]],
                    "price_per_night": item["ppn"],
                    "nights": item["nights"],
                    "subtotal": item["ppn"] * item["nights"],
                },
            )
            out[item["booking_code"]] = booking
        return out

    def _seed_services(self):
        category_data = [
            ("Spa", "spa"),
            ("Restaurant", "restaurant"),
            ("Transport", "transport"),
        ]
        category_map = {}
        for name, slug in category_data:
            category_map[slug], _ = ServiceCategory.objects.update_or_create(slug=slug, defaults={"name": name})

        service_data = [
            ("spa", "Spa 60 phut", "Massage toan than", Decimal("800000.00"), "per_person"),
            ("restaurant", "Buffet sang", "Breakfast buffet", Decimal("350000.00"), "per_person"),
            ("transport", "Dua don san bay", "Airport pickup", Decimal("500000.00"), "per_trip"),
        ]
        for slug, name, desc, price, unit in service_data:
            Service.objects.update_or_create(
                category=category_map[slug],
                name=name,
                defaults={"description": desc, "price": price, "unit": unit},
            )

    def _seed_notifications(self, users, bookings):
        data = [
            (
                "Booking confirmed",
                NotificationType.BOOKING_CONFIRMED,
                "Booking BK20260001 has been confirmed.",
                False,
                {"booking_code": "BK20260001", "booking_id": str(bookings["BK20260001"].id)},
            ),
            (
                "Payment received",
                NotificationType.PAYMENT_RECEIVED,
                "Payment for BK20260001 received.",
                False,
                {"booking_code": "BK20260001"},
            ),
        ]
        for title, ntype, body, is_read, meta in data:
            Notification.objects.update_or_create(
                user=users["customer"],
                title=title,
                defaults={
                    "notification_type": ntype,
                    "body": body,
                    "channel": NotificationChannel.IN_APP,
                    "is_read": is_read,
                    "metadata": meta,
                },
            )

    def _seed_payments(self, bookings):
        data = [
            (bookings["BK20260001"], Decimal("2800000.00"), PaymentMethod.VNPAY, PaymentStatus.COMPLETED, "VNP20260524080000", timezone.make_aware(datetime(2026, 5, 24, 8, 5, 0))),
            (bookings["BK20260003"], Decimal("800000.00"), PaymentMethod.CASH, PaymentStatus.COMPLETED, "", timezone.make_aware(datetime(2026, 5, 24, 14, 10, 0))),
            (bookings["BK20260002"], Decimal("6400000.00"), PaymentMethod.BANK_TRANSFER, PaymentStatus.PENDING, "", None),
        ]
        for booking, amount, method, status, tx_ref, paid_at in data:
            Payment.objects.update_or_create(
                booking=booking,
                method=method,
                defaults={
                    "amount": amount,
                    "status": status,
                    "transaction_ref": tx_ref,
                    "paid_at": paid_at,
                },
            )

    def _seed_housekeeping_tasks(self, users, rooms):
        data = [
            ("102", TaskType.CHECKOUT_CLEAN, TaskStatus.PENDING, TaskPriority.HIGH, "Guest checked out, clean ASAP."),
            ("103", TaskType.DAILY_CLEAN, TaskStatus.IN_PROGRESS, TaskPriority.NORMAL, ""),
            ("302", TaskType.MAINTENANCE, TaskStatus.PENDING, TaskPriority.HIGH, "AC issue, need support."),
        ]
        for room_number, task_type, status, priority, notes in data:
            HousekeepingTask.objects.update_or_create(
                room=rooms[room_number],
                task_type=task_type,
                status=status,
                defaults={
                    "assigned_to": users["housekeeping"],
                    "priority": priority,
                    "notes": notes,
                },
            )

