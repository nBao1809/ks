from decimal import Decimal
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Case, DecimalField, F, Sum, Value, When
from django.db.models.functions import Coalesce
from django.utils import timezone
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image as RLImage, SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from app.models import Booking, BookingPaymentStatus, BookingStatus
from app.core.exceptions import BusinessException
from app.models import Invoice, Payment, PaymentMethod, PaymentStatus, Transaction
from app.views.payments.services.vnpay_service import VNPayService


class PaymentService:
    _fonts_registered = False
    LOGO_URL = 'https://res.cloudinary.com/dblzpkokm/image/upload/v1779649199/hotel4_ejlhzz.jpg'
    COMPANY_PHONE = '0901 234 567'
    COMPANY_ADDRESS = '123 Ngô Gia Tự, P. 3, Q. 10, TP. Hồ Chí Minh'
    COMPANY_TAX_ID = '0312345678'

    @staticmethod
    def sync_booking_payment(booking):
        paid = (
            Payment.objects.filter(
                booking_id=booking.id,
                status=PaymentStatus.COMPLETED,
                is_active=True,
            ).aggregate(total=Sum('amount'))['total']
            or Decimal('0')
        )
        booking.paid_amount = paid
        if paid <= 0:
            booking.payment_status = BookingPaymentStatus.UNPAID
        elif paid >= booking.total_amount:
            booking.payment_status = BookingPaymentStatus.PAID
        else:
            booking.payment_status = BookingPaymentStatus.PARTIAL
        booking.save(update_fields=['paid_amount', 'payment_status', 'updated_at'])
        return booking


    @staticmethod
    def _register_pdf_fonts():
        if PaymentService._fonts_registered:
            return
        pdfmetrics.registerFont(TTFont('SmartHotel', r'C:\\Windows\\Fonts\\arial.ttf'))
        pdfmetrics.registerFont(TTFont('SmartHotel-Bold', r'C:\\Windows\\Fonts\\arialbd.ttf'))
        pdfmetrics.registerFontFamily(
            'SmartHotel',
            normal='SmartHotel',
            bold='SmartHotel-Bold',
            italic='SmartHotel',
            boldItalic='SmartHotel-Bold',
        )
        PaymentService._fonts_registered = True

    @staticmethod
    def _build_logo_image(width=22 * mm, height=22 * mm):
        try:
            logo_bytes = urlopen(PaymentService.LOGO_URL, timeout=8).read()
            return RLImage(BytesIO(logo_bytes), width=width, height=height)
        except Exception:
            return None

    @staticmethod
    def _render_invoice_pdf(invoice):
        PaymentService._register_pdf_fonts()
        booking = invoice.booking
        customer = booking.customer

        pdf_buffer = BytesIO()
        pdf_doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=A4,
            rightMargin=18 * mm,
            leftMargin=18 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
            title=f'Invoice {invoice.invoice_number}',
            author='Smart Hotel',
        )
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='InvoiceHeader', parent=styles['Title'], fontName='SmartHotel-Bold', fontSize=22, leading=26, textColor=colors.white))
        styles.add(ParagraphStyle(name='InvoiceSubHeader', parent=styles['BodyText'], fontName='SmartHotel', fontSize=9.5, leading=13, textColor=colors.HexColor('#D7DBF0')))
        styles.add(ParagraphStyle(name='InvoiceLabel', parent=styles['BodyText'], fontName='SmartHotel-Bold', fontSize=9.5, leading=12, textColor=colors.HexColor('#1A1A2E')))
        styles.add(ParagraphStyle(name='InvoiceText', parent=styles['BodyText'], fontName='SmartHotel', fontSize=10.5, leading=14, textColor=colors.HexColor('#222222')))
        styles.add(ParagraphStyle(name='InvoiceTotal', parent=styles['BodyText'], fontName='SmartHotel-Bold', fontSize=12, leading=15, textColor=colors.HexColor('#1A1A2E')))

        issue_date = invoice.issued_at.strftime('%d/%m/%Y %H:%M') if invoice.issued_at else ''
        logo = PaymentService._build_logo_image()
        logo_block = logo if logo else Paragraph('Smart Hotel', styles['InvoiceHeader'])
        header_table = Table([
            [
                logo_block,
                Paragraph(
                    f'<b>HÓA ĐƠN ĐIỆN TỬ</b><br/>'
                    f'<b>Số hóa đơn:</b> {invoice.invoice_number}<br/>'
                    f'<b>Ngày phát hành:</b> {issue_date}<br/>'
                    f'<b>Trạng thái:</b> Đã thanh toán',
                    styles['InvoiceSubHeader'],
                ),
            ]
        ], colWidths=[40 * mm, 133 * mm])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#1A1A2E')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('LEFTPADDING', (0, 0), (-1, -1), 14),
            ('RIGHTPADDING', (0, 0), (-1, -1), 14),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#1A1A2E')),
        ]))

        info_table = Table([
            [
                Paragraph(
                    '<b>Đơn vị bán hàng</b><br/>'
                    'Smart Hotel<br/>'
                    'Hệ thống quản lý khách sạn<br/>'
                    f'Địa chỉ: {PaymentService.COMPANY_ADDRESS}<br/>'
                    f'Điện thoại: {PaymentService.COMPANY_PHONE}<br/>'
                    f'MST: {PaymentService.COMPANY_TAX_ID}',
                    styles['InvoiceText'],
                ),
                Paragraph(
                    f'<b>Khách hàng</b><br/>{customer.full_name}<br/>{customer.email}<br/>'
                    f'<b>Booking:</b> {booking.booking_code}<br/>'
                    f'<b>Nhận phòng:</b> {booking.check_in_date} | <b>Trả phòng:</b> {booking.check_out_date}',
                    styles['InvoiceText'],
                ),
            ]
        ], colWidths=[86 * mm, 87 * mm])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F7F8FC')),
            ('BOX', (0, 0), (-1, -1), 0.6, colors.HexColor('#D9D9E5')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D9D9E5')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))

        elements = [header_table, Spacer(1, 5 * mm), info_table, Spacer(1, 7 * mm)]

        # Tính tiền phòng và tiền dịch vụ
        room_total = Decimal('0')
        service_total = Decimal('0')
        
        table_data = [[
            Paragraph('<b>Mô tả</b>', styles['InvoiceLabel']),
            Paragraph('<b>Đêm</b>', styles['InvoiceLabel']),
            Paragraph('<b>Thành tiền</b>', styles['InvoiceLabel']),
        ]]
        
        # Thêm dòng phòng
        for br in booking.booking_rooms.all():
            room_total += br.subtotal
            table_data.append([
                Paragraph(f'{br.room_type.name} - {br.room.room_number}', styles['InvoiceText']),
                Paragraph(str(br.nights), styles['InvoiceText']),
                Paragraph(f'{br.subtotal:,.0f} đ', styles['InvoiceText']),
            ])
        
        # Thêm dòng dịch vụ
        from app.models import ServiceOrderStatus
        for order in booking.service_orders.filter(status=ServiceOrderStatus.CONFIRMED, is_active=True):
            service_total += order.total_amount
            for item in order.items.filter(is_active=True):
                table_data.append([
                    Paragraph(f'{item.description or item.service.name}', styles['InvoiceText']),
                    Paragraph('1', styles['InvoiceText']),
                    Paragraph(f'{item.subtotal:,.0f} đ', styles['InvoiceText']),
                ])
        
        table = Table(table_data, colWidths=[95 * mm, 20 * mm, 40 * mm], repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E9ECF8')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1A1A2E')),
            ('FONTNAME', (0, 0), (-1, -1), 'SmartHotel'),
            ('FONTSIZE', (0, 0), (-1, -1), 9.5),
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D9D9E5')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FAFAFC')]),
            ('TOPPADDING', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 6 * mm))

        # Xây dựng bảng tóm tắt với tiền dịch vụ
        summary_rows = [
            [Paragraph('Tạm tính (Phòng)', styles['InvoiceText']), Paragraph(f'{room_total:,.0f} đ', styles['InvoiceText'])],
        ]
        if service_total > Decimal('0'):
            summary_rows.append(
                [Paragraph('Tiền dịch vụ', styles['InvoiceText']), Paragraph(f'{service_total:,.0f} đ', styles['InvoiceText'])]
            )
        summary_rows.extend([
            [Paragraph('Chiết khấu', styles['InvoiceText']), Paragraph(f'{invoice.discount:,.0f} đ', styles['InvoiceText'])],
            [Paragraph('Tổng cộng', styles['InvoiceTotal']), Paragraph(f'{invoice.total:,.0f} đ', styles['InvoiceTotal'])],
        ])
        
        summary_table = Table(summary_rows, colWidths=[110 * mm, 55 * mm])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#FFF1D6')),
            ('BOX', (0, 0), (-1, -1), 0.6, colors.HexColor('#D9D9E5')),
            ('INNERGRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#D9D9E5')),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 6 * mm))
        elements.append(Paragraph('Cảm ơn bạn đã sử dụng dịch vụ Smart Hotel.', styles['InvoiceText']))
        pdf_doc.build(elements)
        pdf_bytes = pdf_buffer.getvalue()
        pdf_buffer.close()
        return pdf_bytes

    @staticmethod
    def _store_invoice_pdf(invoice, pdf_bytes):
        filename = f'invoices/{invoice.invoice_number}.pdf'
        saved_name = default_storage.save(filename, ContentFile(pdf_bytes))
        invoice.pdf_url = default_storage.url(saved_name)
        invoice.save(update_fields=['pdf_url', 'updated_at'])
        return invoice.pdf_url

    @staticmethod
    def _generate_invoice_number():
        prefix = timezone.now().strftime('INV-%Y')
        count = Invoice.objects.filter(invoice_number__startswith=prefix).count() + 1
        return f'{prefix}-{count:05d}'

    @staticmethod
    def _generate_transaction_ref():
        return f'TXN-{timezone.now().strftime("%Y%m%d%H%M%S")}-{Payment.objects.count() + 1}'

    @staticmethod
    def _booking_payable_total(booking):
        subtotal = booking.total_amount
        return subtotal.quantize(Decimal('0.01'))

    @staticmethod
    def _booking_net_paid(booking):
        # Net paid = all credit transactions - all debit(refund) transactions.
        paid_data = Transaction.objects.filter(payment__booking=booking, is_active=True).aggregate(
            net=Coalesce(
                Sum(
                    Case(
                        When(transaction_type='credit', then=F('amount')),
                        When(transaction_type='debit', then=-F('amount')),
                        default=Value(Decimal('0.00')),
                        output_field=DecimalField(max_digits=14, decimal_places=2),
                    )
                ),
                Value(Decimal('0.00')),
            )
        )
        return Decimal(paid_data['net']).quantize(Decimal('0.01'))

    @staticmethod
    def _booking_remaining_amount(booking):
        remaining = PaymentService._booking_payable_total(booking) - PaymentService._booking_net_paid(booking)
        if remaining < Decimal('0.00'):
            return Decimal('0.00')
        return remaining.quantize(Decimal('0.01'))

    @staticmethod
    def _ensure_invoice(booking):
        invoice = Invoice.objects.filter(booking=booking).first()
        if invoice:
            expected_total = (invoice.subtotal - invoice.discount).quantize(Decimal('0.01'))
            update_fields = []
            invoice_changed = False
            if invoice.tax != Decimal('0.00'):
                invoice.tax = Decimal('0.00')
                update_fields.append('tax')
                invoice_changed = True
            if invoice.total != expected_total:
                invoice.total = expected_total
                update_fields.append('total')
                invoice_changed = True
            # Cập nhật subtotal nếu booking.total_amount thay đổi (do thêm dịch vụ)
            if invoice.subtotal != booking.total_amount:
                invoice.subtotal = booking.total_amount
                expected_total = (invoice.subtotal - invoice.discount).quantize(Decimal('0.01'))
                invoice.total = expected_total
                if 'subtotal' not in update_fields:
                    update_fields.append('subtotal')
                if 'total' not in update_fields:
                    update_fields.append('total')
                invoice_changed = True
            if update_fields:
                update_fields.append('updated_at')
                invoice.save(update_fields=update_fields)
            if invoice_changed or not invoice.pdf_url:
                pdf_bytes = PaymentService._render_invoice_pdf(invoice)
                PaymentService._store_invoice_pdf(invoice, pdf_bytes)
            return invoice, False

        subtotal = booking.total_amount
        tax = Decimal('0.00')
        total = subtotal.quantize(Decimal('0.01'))
        invoice = Invoice.objects.create(
            invoice_number=PaymentService._generate_invoice_number(),
            booking=booking,
            subtotal=subtotal,
            tax=tax,
            discount=Decimal('0'),
            total=total,
        )
        pdf_bytes = PaymentService._render_invoice_pdf(invoice)
        PaymentService._store_invoice_pdf(invoice, pdf_bytes)
        return invoice, True

    @staticmethod
    def _send_payment_confirmation_email(payment_id):
        """Gửi email xác nhận thanh toán (hóa đơn tạm tính) khi VNPay thanh toán thành công"""
        payment = Payment.objects.select_related('booking', 'booking__customer').prefetch_related(
            'booking__booking_rooms__room',
            'booking__booking_rooms__room_type',
        ).filter(pk=payment_id, is_active=True).first()
        if not payment:
            return

        booking = payment.booking
        customer = booking.customer
        if not customer.email:
            return

        # Tính tiền phòng và tiền dịch vụ
        room_total = Decimal('0')
        service_total = Decimal('0')
        
        # Dòng chi tiết phòng
        line_rows = []
        for br in booking.booking_rooms.all():
            room_total += br.subtotal
            line_rows.append(
                f'<tr>'
                f'<td style="padding:8px;border-bottom:1px solid #eee;">{br.room_type.name} - {br.room.room_number}</td>'
                f'<td style="padding:8px;border-bottom:1px solid #eee;text-align:center;">{br.nights}</td>'
                f'<td style="padding:8px;border-bottom:1px solid #eee;text-align:right;">{br.subtotal:,.0f} đ</td>'
                f'</tr>'
            )
        
        # Dòng chi tiết dịch vụ đã confirm
        from app.models import ServiceOrderStatus
        for order in booking.service_orders.filter(status=ServiceOrderStatus.CONFIRMED, is_active=True):
            service_total += order.total_amount
            for item in order.items.filter(is_active=True):
                line_rows.append(
                    f'<tr>'
                    f'<td style="padding:8px;border-bottom:1px solid #eee;">{item.description or item.service.name}</td>'
                    f'<td style="padding:8px;border-bottom:1px solid #eee;text-align:center;">1</td>'
                    f'<td style="padding:8px;border-bottom:1px solid #eee;text-align:right;">{item.subtotal:,.0f} đ</td>'
                    f'</tr>'
                )

        total_confirmed = room_total + service_total
        
        service_fee_row = ''
        if service_total > Decimal('0'):
            service_fee_row = f'<p style="margin:0 0 4px"><b>Tiền dịch vụ:</b> {service_total:,.0f} đ</p>'

        subject = f'[Smart Hotel] Xác nhận thanh toán - {booking.booking_code}'
        text_body = (
            f'Xin chào {customer.full_name},\n\n'
            f'Cảm ơn bạn đã thanh toán cho booking {booking.booking_code}.\n\n'
            f'Smart Hotel | MST: {PaymentService.COMPANY_TAX_ID} | SĐT: {PaymentService.COMPANY_PHONE}\n'
            f'Địa chỉ: {PaymentService.COMPANY_ADDRESS}\n\n'
            f'---ĐƠN XÁC NHẬN THANH TOÁN (HÓA ĐƠN TẠM TÍNH)---\n'
            f'Booking: {booking.booking_code}\n'
            f'Nhận phòng: {booking.check_in_date}\n'
            f'Trả phòng: {booking.check_out_date}\n'
            f'Số tiền thanh toán: {payment.amount:,.0f} đ\n'
            f'Phương thức: VNPay\n'
            f'Ngày thanh toán: {payment.paid_at.strftime("%d/%m/%Y %H:%M") if payment.paid_at else ""}\n\n'
            f'LƯU Ý: Hóa đơn này là hóa đơn tạm tính chỉ bao gồm chi phí phòng và các dịch vụ đã xác nhận.\n'
            f'Chưa bao gồm các phí dịch vụ phát sinh trong quá trình ở (minibar, hư hỏng, dịch vụ bổ sung...).\n'
            f'Hóa đơn cuối cùng sẽ được cập nhật sau khi checkout.\n\n'
            f'Trân trọng,\nSmart Hotel'
        )
        
        html_body = f'''
        <div style="font-family:Arial,sans-serif;color:#222;line-height:1.6">
            <div style="display:flex;align-items:center;gap:14px;margin-bottom:10px;">
                <img src="{PaymentService.LOGO_URL}" alt="Smart Hotel" style="width:56px;height:56px;border-radius:12px;object-fit:cover;" />
                <div>
                    <h2 style="margin:0 0 4px">Smart Hotel</h2>
                    <div style="font-size:12px;color:#666;">Xác nhận thanh toán</div>
                </div>
            </div>
            <p>Xin chào <b>{customer.full_name}</b>,</p>
            <p>Cảm ơn bạn đã thanh toán cho booking <b>{booking.booking_code}</b>. Đây là đơn xác nhận thanh toán của chúng tôi.</p>
            <p style="margin:0 0 12px;font-size:13px;color:#555;">
                Địa chỉ: {PaymentService.COMPANY_ADDRESS}<br/>
                Điện thoại: {PaymentService.COMPANY_PHONE}<br/>
                MST: {PaymentService.COMPANY_TAX_ID}
            </p>
            
            <div style="background:#f7f7fb;border:1px solid #e7e7ef;border-radius:12px;padding:16px;margin:16px 0;">
                <h3 style="margin:0 0 12px;color:#1a1a2e;">THÔNG TIN THANH TOÁN</h3>
                <p style="margin:0 0 6px"><b>Booking:</b> {booking.booking_code}</p>
                <p style="margin:0 0 6px"><b>Nhận phòng:</b> {booking.check_in_date}</p>
                <p style="margin:0 0 6px"><b>Trả phòng:</b> {booking.check_out_date}</p>
                <p style="margin:0 0 6px"><b>Số tiền thanh toán:</b> {payment.amount:,.0f} đ</p>
                <p style="margin:0 0 6px"><b>Phương thức:</b> VNPay</p>
                <p style="margin:0 0 6px"><b>Ngày thanh toán:</b> {payment.paid_at.strftime("%d/%m/%Y %H:%M") if payment.paid_at else ""}</p>
            </div>

            <h3 style="margin:16px 0 8px;color:#1a1a2e;">CHI TIẾT HÓA ĐƠN TẠM TÍNH</h3>
            <table style="width:100%;border-collapse:collapse;margin:16px 0;">
                <thead>
                    <tr>
                        <th style="text-align:left;padding:8px;border-bottom:2px solid #ddd;">Mô tả</th>
                        <th style="text-align:center;padding:8px;border-bottom:2px solid #ddd;">Đêm/SL</th>
                        <th style="text-align:right;padding:8px;border-bottom:2px solid #ddd;">Thành tiền</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(line_rows)}
                </tbody>
            </table>

            <div style="background:#fffaf0;border-left:4px solid #ff9800;padding:12px;margin:16px 0;">
                <p style="margin:0 0 4px"><b>Tạm tính (Phòng):</b> {room_total:,.0f} đ</p>
                {service_fee_row}
                <p style="margin:0 0 0"><b>Tổng tiền hóa đơn tạm tính:</b> {total_confirmed:,.0f} đ</p>
            </div>

            <div style="background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:14px;margin:16px 0;color:#856404;">
                <p style="margin:0 0 8px;font-weight:bold;">⚠️ LƯU Ý QUAN TRỌNG</p>
                <p style="margin:0 0 8px;">Hóa đơn này là <b>hóa đơn tạm tính</b> chỉ bao gồm:</p>
                <ul style="margin:8px 0;padding-left:20px;">
                    <li>Chi phí phòng</li>
                    <li>Các dịch vụ đã được xác nhận trước thanh toán</li>
                </ul>
                <p style="margin:8px 0;">Hóa đơn này <b>CHƯA bao gồm</b> các chi phí phát sinh trong quá trình ở như:</p>
                <ul style="margin:8px 0;padding-left:20px;">
                    <li>Dịch vụ minibar, đồ uống</li>
                    <li>Dịch vụ giặt là, spa bổ sung</li>
                    <li>Chi phí hư hỏng hoặc mất mát</li>
                    <li>Các dịch vụ khác được thêm trong quá trình ở</li>
                </ul>
                <p style="margin:8px 0 0;">Hóa đơn cuối cùng sẽ được cập nhật và gửi lại sau khi bạn checkout.</p>
            </div>

            <p style="margin:16px 0 0;text-align:center;font-size:12px;color:#666;">
                Cảm ơn bạn đã chọn Smart Hotel. Chúng tôi mong được phục vụ bạn!
            </p>
        </div>
        '''

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[customer.email],
        )
        email.attach_alternative(html_body, 'text/html')
        email.send(fail_silently=True)

    @staticmethod
    def _send_invoice_email(invoice_id):
        PaymentService._register_pdf_fonts()
        invoice = Invoice.objects.select_related('booking', 'booking__customer').prefetch_related(
            'booking__booking_rooms__room',
            'booking__booking_rooms__room_type',
        ).filter(pk=invoice_id).first()
        if not invoice:
            return

        booking = invoice.booking
        customer = booking.customer
        if not customer.email:
            return
        pdf_bytes = PaymentService._render_invoice_pdf(invoice)
        pdf_url = invoice.pdf_url or PaymentService._store_invoice_pdf(invoice, pdf_bytes)
        pdf_filename = Path(pdf_url).name if pdf_url else f'invoice-{invoice.invoice_number}.pdf'

        # Tính tiền phòng và tiền dịch vụ
        room_total = Decimal('0')
        service_total = Decimal('0')
        
        # Dòng chi tiết phòng
        line_rows = []
        for br in booking.booking_rooms.all():
            room_total += br.subtotal
            line_rows.append(
                f'<tr>'
                f'<td style="padding:8px;border-bottom:1px solid #eee;">{br.room_type.name} - {br.room.room_number}</td>'
                f'<td style="padding:8px;border-bottom:1px solid #eee;text-align:center;">{br.nights}</td>'
                f'<td style="padding:8px;border-bottom:1px solid #eee;text-align:right;">{br.subtotal:,.0f} đ</td>'
                f'</tr>'
            )
        
        # Dòng chi tiết dịch vụ
        from app.models import ServiceOrderStatus
        for order in booking.service_orders.filter(status=ServiceOrderStatus.CONFIRMED, is_active=True):
            service_total += order.total_amount
            for item in order.items.filter(is_active=True):
                line_rows.append(
                    f'<tr>'
                    f'<td style="padding:8px;border-bottom:1px solid #eee;">{item.description or item.service.name}</td>'
                    f'<td style="padding:8px;border-bottom:1px solid #eee;text-align:center;">1</td>'
                    f'<td style="padding:8px;border-bottom:1px solid #eee;text-align:right;">{item.subtotal:,.0f} đ</td>'
                    f'</tr>'
                )

        subject = f'[Smart Hotel] Hóa đơn {invoice.invoice_number}'
        text_body = (
            f'Xin chào {customer.full_name},\n\n'
                        f'Đính kèm file PDF bản sao điện tử hóa đơn cho booking {booking.booking_code}.\n\n'
                        f'Smart Hotel | MST: {PaymentService.COMPANY_TAX_ID} | SĐT: {PaymentService.COMPANY_PHONE}\n'
                        f'Địa chỉ: {PaymentService.COMPANY_ADDRESS}\n\n'
            f'Số hóa đơn: {invoice.invoice_number}\n'
            f'Tạm tính (Phòng): {room_total:,.0f} đ\n'
        )
        if service_total > Decimal('0'):
            text_body += f'Tiền dịch vụ: {service_total:,.0f} đ\n'
        text_body += (
            f'Chiết khấu: {invoice.discount:,.0f} đ\n'
            f'Tổng cộng: {invoice.total:,.0f} đ\n\n'
            f'Trân trọng,\nSmart Hotel'
        )
        
        # HTML email body
        service_fee_row = ''
        if service_total > Decimal('0'):
            service_fee_row = f'<p style="margin:0 0 4px"><b>Tiền dịch vụ:</b> {service_total:,.0f} đ</p>'
        
        html_body = f'''
        <div style="font-family:Arial,sans-serif;color:#222;line-height:1.6">
                    <div style="display:flex;align-items:center;gap:14px;margin-bottom:10px;">
                        <img src="{PaymentService.LOGO_URL}" alt="Smart Hotel" style="width:56px;height:56px;border-radius:12px;object-fit:cover;" />
                        <div>
                            <h2 style="margin:0 0 4px">Smart Hotel</h2>
                            <div style="font-size:12px;color:#666;">Hóa đơn điện tử</div>
                        </div>
                    </div>
          <p>Xin chào <b>{customer.full_name}</b>,</p>
                    <p>Đây là file PDF bản sao điện tử hóa đơn cho booking <b>{booking.booking_code}</b>.</p>
                    <p style="margin:0 0 12px;font-size:13px;color:#555;">
                        Địa chỉ: {PaymentService.COMPANY_ADDRESS}<br/>
                        Điện thoại: {PaymentService.COMPANY_PHONE}<br/>
                        MST: {PaymentService.COMPANY_TAX_ID}
                    </p>
          <div style="background:#f7f7fb;border:1px solid #e7e7ef;border-radius:12px;padding:16px;margin:16px 0;">
            <p style="margin:0 0 6px"><b>Số hóa đơn:</b> {invoice.invoice_number}</p>
            <p style="margin:0 0 6px"><b>Nhận phòng:</b> {booking.check_in_date}</p>
            <p style="margin:0 0 6px"><b>Trả phòng:</b> {booking.check_out_date}</p>
            <p style="margin:0 0 6px"><b>Tổng cộng:</b> {invoice.total:,.0f} đ</p>
          </div>
          <table style="width:100%;border-collapse:collapse;margin:16px 0;">
            <thead>
              <tr>
                <th style="text-align:left;padding:8px;border-bottom:2px solid #ddd;">Mô tả</th>
                <th style="text-align:center;padding:8px;border-bottom:2px solid #ddd;">Đêm/SL</th>
                <th style="text-align:right;padding:8px;border-bottom:2px solid #ddd;">Thành tiền</th>
              </tr>
            </thead>
            <tbody>
              {''.join(line_rows)}
            </tbody>
          </table>
          <p style="margin:0 0 4px"><b>Tạm tính (Phòng):</b> {room_total:,.0f} đ</p>
          {service_fee_row}
          <p style="margin:0 0 4px"><b>Chiết khấu:</b> {invoice.discount:,.0f} đ</p>
          <p style="margin:0 0 16px"><b>Tổng cộng:</b> {invoice.total:,.0f} đ</p>
        </div>
        '''

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[customer.email],
        )
        email.attach_alternative(html_body, 'text/html')
        email.attach(pdf_filename, pdf_bytes, 'application/pdf')
        email.send(fail_silently=True)

    @staticmethod
    @transaction.atomic
    def create_payment(booking_id, amount, method, user, request=None, bank_code=None, locale='vn', app_return_url=''):
        booking = Booking.objects.filter(pk=booking_id, is_active=True).first()
        if not booking:
            raise BusinessException('Booking không tồn tại', code='NOT_FOUND', status_code=404)
        if booking.status == BookingStatus.CANCELLED:
            raise BusinessException('Booking đã hủy', code='INVALID_BOOKING')

        remaining = PaymentService._booking_remaining_amount(booking)
        if remaining <= Decimal('0.00'):
            raise BusinessException('Booking đã được thanh toán đủ', code='ALREADY_PAID')

        amount = Decimal(amount).quantize(Decimal('0.01'))
        if amount <= Decimal('0.00'):
            raise BusinessException('Số tiền thanh toán phải lớn hơn 0', code='INVALID_AMOUNT')
        if amount > remaining:
            raise BusinessException(
                f'Số tiền vượt quá phần còn lại ({remaining:,.0f} đ)',
                code='INVALID_AMOUNT',
                status_code=422,
            )

        payment = Payment.objects.create(
            booking=booking,
            amount=amount,
            method=method,
            status=PaymentStatus.PENDING,
        )

        if method == PaymentMethod.CASH:
            payment.status = PaymentStatus.COMPLETED
            payment.paid_at = timezone.now()
            payment.transaction_ref = PaymentService._generate_transaction_ref()
            payment.save()
            Transaction.objects.create(
                payment=payment,
                transaction_type='credit',
                amount=amount,
                note='Cash payment',
            )
            if booking.status == BookingStatus.PENDING:
                from app.views.bookings.services.booking_service import BookingService
                BookingService.transition(booking, BookingStatus.CONFIRMED, user, 'Paid cash')
            try:
                from app.views.notifications.services.notification_service import NotificationService
                NotificationService.payment_received(payment)
            except Exception:
                pass
            invoice, created = PaymentService._ensure_invoice(booking)
            PaymentService.sync_booking_payment(booking)
            transaction.on_commit(lambda invoice_id=invoice.id: PaymentService._send_invoice_email(invoice_id))
        elif method == PaymentMethod.VNPAY:
            payment.save()
            payment.transaction_ref = VNPayService.txn_ref_from_payment_id(payment.id)
            payment.payment_url = VNPayService.build_payment_url(
                payment, booking, request=request, bank_code=bank_code, locale=locale, app_return_url=app_return_url,
            )
            payment.save(update_fields=['transaction_ref', 'payment_url', 'updated_at'])
        elif method in (PaymentMethod.MOMO, PaymentMethod.CARD, PaymentMethod.BANK_TRANSFER):
            ref = PaymentService._generate_transaction_ref()
            payment.transaction_ref = ref
            payment.payment_url = f'https://sandbox.payment.local/pay/{ref}'
            payment.save()
        else:
            payment.save()

        return payment

    @staticmethod
    def _find_payment_by_vnp_txn_ref(txn_ref):
        payment_id = VNPayService.payment_id_from_txn_ref(txn_ref)
        return Payment.objects.select_related('booking').filter(pk=payment_id).first()

    @staticmethod
    def _complete_vnpay_payment(payment, vnp_params):
        payment.status = PaymentStatus.COMPLETED
        payment.paid_at = timezone.now()
        payment.vnp_transaction_no = str(vnp_params.get('vnp_TransactionNo', ''))
        payment.gateway_meta = dict(vnp_params)
        payment.save()
        Transaction.objects.create(
            payment=payment,
            transaction_type='credit',
            amount=payment.amount,
            note=f'VNPay {payment.vnp_transaction_no}',
        )
        booking = payment.booking
        if booking.status == BookingStatus.PENDING:
            from app.views.bookings.services.booking_service import BookingService
            BookingService.transition(booking, BookingStatus.CONFIRMED, None, 'VNPay payment completed')
        try:
            from app.views.notifications.services.notification_service import NotificationService
            NotificationService.payment_received(payment)
        except Exception:
            pass
        invoice, created = PaymentService._ensure_invoice(payment.booking)
        PaymentService.sync_booking_payment(payment.booking)
        transaction.on_commit(lambda payment_id=payment.id: PaymentService._send_payment_confirmation_email(payment_id))
        return payment

    @staticmethod
    @transaction.atomic
    def process_vnpay_ipn(vnp_params):
        txn_ref = vnp_params.get('vnp_TxnRef', '')
        payment = PaymentService._find_payment_by_vnp_txn_ref(txn_ref)
        if not payment:
            return {'RspCode': '01', 'Message': 'Order Not Found'}

        if payment.status == PaymentStatus.COMPLETED:
            return {'RspCode': '02', 'Message': 'Order already confirmed'}

        expected_amount = int(Decimal(payment.amount) * 100)
        if int(vnp_params.get('vnp_Amount', 0)) != expected_amount:
            return {'RspCode': '04', 'Message': 'Invalid amount'}

        if VNPayService.is_payment_success(vnp_params):
            PaymentService._complete_vnpay_payment(payment, vnp_params)
        elif payment.status == PaymentStatus.PENDING:
            payment.status = PaymentStatus.FAILED
            payment.gateway_meta = dict(vnp_params)
            payment.save(update_fields=['status', 'gateway_meta', 'updated_at'])

        return {'RspCode': '00', 'Message': 'Confirm Success'}

    @staticmethod
    @transaction.atomic
    def process_vnpay_return(vnp_params):
        txn_ref = vnp_params.get('vnp_TxnRef', '')
        payment = PaymentService._find_payment_by_vnp_txn_ref(txn_ref)
        if not payment:
            raise BusinessException('Payment không tồn tại', code='NOT_FOUND', status_code=404)

        expected_amount = int(Decimal(payment.amount) * 100)
        if int(vnp_params.get('vnp_Amount', 0)) != expected_amount:
            raise BusinessException('Số tiền không khớp', code='INVALID_AMOUNT')

        if payment.status == PaymentStatus.PENDING and VNPayService.is_payment_success(vnp_params):
            PaymentService._complete_vnpay_payment(payment, vnp_params)
        elif payment.status == PaymentStatus.PENDING and not VNPayService.is_payment_success(vnp_params):
            payment.status = PaymentStatus.FAILED
            payment.gateway_meta = dict(vnp_params)
            payment.save(update_fields=['status', 'gateway_meta', 'updated_at'])

        return payment, vnp_params

    @staticmethod
    @transaction.atomic
    def complete_webhook(transaction_ref):
        payment = Payment.objects.select_related('booking').filter(
            transaction_ref=transaction_ref,
            status=PaymentStatus.PENDING,
        ).first()
        if not payment:
            raise BusinessException('Payment không tồn tại', code='NOT_FOUND', status_code=404)
        payment.status = PaymentStatus.COMPLETED
        payment.paid_at = timezone.now()
        payment.save()
        Transaction.objects.create(
            payment=payment,
            transaction_type='credit',
            amount=payment.amount,
            note='Online payment',
        )
        booking = payment.booking
        if booking.status == BookingStatus.PENDING:
            from app.views.bookings.services.booking_service import BookingService
            BookingService.transition(booking, BookingStatus.CONFIRMED, None, 'Payment completed')
        try:
            from app.views.notifications.services.notification_service import NotificationService
            NotificationService.payment_received(payment)
        except Exception:
            pass
        invoice, created = PaymentService._ensure_invoice(payment.booking)
        PaymentService.sync_booking_payment(booking)
        transaction.on_commit(lambda invoice_id=invoice.id: PaymentService._send_invoice_email(invoice_id))
        return payment

    @staticmethod
    @transaction.atomic
    def refund(payment_id, amount, reason, user):
        payment = Payment.objects.filter(pk=payment_id).first()
        if not payment:
            raise BusinessException('Payment không tồn tại', code='NOT_FOUND', status_code=404)
        if payment.status != PaymentStatus.COMPLETED:
            raise BusinessException('Chỉ hoàn tiền payment đã completed', code='INVALID_STATUS')
        if amount > payment.amount:
            raise BusinessException('Số tiền hoàn vượt quá thanh toán', code='INVALID_AMOUNT')
        payment.status = PaymentStatus.REFUNDED
        payment.save()
        Transaction.objects.create(
            payment=payment,
            transaction_type='debit',
            amount=amount,
            note=reason or 'Refund',
        )
        PaymentService.sync_booking_payment(payment.booking)
        return payment

    @staticmethod
    @transaction.atomic
    def create_invoice(booking_id):
        booking = Booking.objects.prefetch_related('booking_rooms').filter(pk=booking_id).first()
        if not booking:
            raise BusinessException('Booking không tồn tại', code='NOT_FOUND', status_code=404)
        invoice, _ = PaymentService._ensure_invoice(booking)
        return invoice

    @staticmethod
    def get_payments_for_user(user, booking_id=None):
        qs = Payment.objects.select_related('booking', 'booking__customer').filter(is_active=True)
        if booking_id:
            qs = qs.filter(booking_id=booking_id)
        if user.is_superuser:
            return qs
        if user.role == 'customer':
            return qs.filter(booking__customer_id=user.id)
        if user.role in ('manager', 'receptionist'):
            return qs
        return qs.none()

