from datetime import date, timedelta
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.conf import settings as django_settings
from num2words import num2words

from properties.models import Tenant
from .models import Invoice, TenantLedger


def generate_invoice_number(issue_date):
    prefix = f"INV-{issue_date.strftime('%Y-%m')}"
    last_invoice = (
        Invoice.objects.filter(invoice_number__startswith=prefix)
        .order_by('-invoice_number')
        .first()
    )
    if last_invoice:
        last_seq = int(last_invoice.invoice_number.split('-')[-1])
        next_seq = last_seq + 1
    else:
        next_seq = 1
    return f"{prefix}-{next_seq:04d}"


def calculate_gst_split(subtotal, gst_percentage, property_state='', tenant_state=''):
    total_gst = subtotal * gst_percentage / Decimal('100')
    is_intrastate = (
        property_state.strip().lower() == tenant_state.strip().lower()
        if property_state and tenant_state
        else True
    )
    if is_intrastate:
        half = total_gst / 2
        return {
            'cgst': half.quantize(Decimal('0.01')),
            'sgst': half.quantize(Decimal('0.01')),
            'igst': Decimal('0'),
            'total_gst': total_gst.quantize(Decimal('0.01')),
        }
    return {
        'cgst': Decimal('0'),
        'sgst': Decimal('0'),
        'igst': total_gst.quantize(Decimal('0.01')),
        'total_gst': total_gst.quantize(Decimal('0.01')),
    }


def create_ledger_entry(tenant, invoice=None, payment=None, transaction_type='invoice',
                        debit=Decimal('0'), credit=Decimal('0'), description='', created_by=None):
    last_entry = (
        TenantLedger.objects.filter(tenant=tenant)
        .order_by('-created_at', '-pk')
        .first()
    )
    prev_balance = last_entry.running_balance if last_entry else Decimal('0')
    running_balance = prev_balance + debit - credit

    return TenantLedger.objects.create(
        tenant=tenant,
        invoice=invoice,
        payment=payment,
        transaction_type=transaction_type,
        debit=debit,
        credit=credit,
        running_balance=running_balance,
        description=description,
        created_by=created_by,
    )


@transaction.atomic
def generate_monthly_invoices(year, month, property_ids=None, created_by=None):
    billing_start = date(year, month, 1)
    billing_end = billing_start + relativedelta(months=1) - timedelta(days=1)

    tenants = Tenant.objects.filter(
        is_active=True,
        lease_start_date__lte=billing_end,
        lease_end_date__gte=billing_start,
        billing_cycle='monthly',
    ).select_related('building')

    if property_ids:
        tenants = tenants.filter(building_id__in=property_ids)

    created_invoices = []
    skipped = []

    for tenant in tenants:
        existing = Invoice.objects.filter(
            tenant=tenant,
            billing_period_start=billing_start,
            billing_period_end=billing_end,
        ).exclude(status='cancelled').exists()

        if existing:
            skipped.append(tenant)
            continue

        issue_date = billing_start
        due_day = min(tenant.payment_due_day, 28)
        due_date = date(year, month, due_day)

        subtotal = tenant.subtotal
        gst = calculate_gst_split(
            subtotal, tenant.gst_percentage,
            property_state=tenant.building.state,
        )
        total = subtotal + gst['total_gst']

        invoice_number = generate_invoice_number(issue_date)

        invoice = Invoice.objects.create(
            invoice_number=invoice_number,
            tenant=tenant,
            property=tenant.building,
            billing_period_start=billing_start,
            billing_period_end=billing_end,
            issue_date=issue_date,
            due_date=due_date,
            rent_amount=tenant.rent_amount,
            maintenance_charges=tenant.maintenance_charges,
            parking_charges=tenant.parking_charges,
            electricity_charges=tenant.electricity_charges,
            other_charges=tenant.other_charges,
            other_charges_description=tenant.other_charges_description,
            subtotal=subtotal,
            gst_percentage=tenant.gst_percentage,
            cgst_amount=gst['cgst'],
            sgst_amount=gst['sgst'],
            igst_amount=gst['igst'],
            total_gst=gst['total_gst'],
            total_amount=total,
            balance_due=total,
            tenant_name=tenant.name,
            tenant_company=tenant.company_name,
            tenant_gst=tenant.gst_number,
            tenant_unit=tenant.unit_number,
            property_name=tenant.building.name,
            property_address=tenant.building.address,
            property_gst=tenant.building.gst_number,
            created_by=created_by,
        )

        create_ledger_entry(
            tenant=tenant,
            invoice=invoice,
            transaction_type='invoice',
            debit=total,
            description=f"Invoice {invoice_number} for {billing_start.strftime('%b %Y')}",
            created_by=created_by,
        )

        created_invoices.append(invoice)

    return created_invoices, skipped


def amount_in_words(amount):
    try:
        rupees = int(amount)
        paise = int(round((amount - rupees) * 100))
        words = num2words(rupees, lang='en_IN').title()
        if paise > 0:
            paise_words = num2words(paise, lang='en_IN').title()
            return f"{words} Rupees and {paise_words} Paise Only"
        return f"{words} Rupees Only"
    except Exception:
        return str(amount)


def generate_invoice_pdf(invoice):
    context = {
        'invoice': invoice,
        'amount_words': amount_in_words(invoice.total_amount),
    }
    html_string = render_to_string('invoices/invoice_pdf.html', context)

    try:
        from io import BytesIO
        from xhtml2pdf import pisa

        result_buffer = BytesIO()
        pisa_status = pisa.CreatePDF(html_string, dest=result_buffer)

        if pisa_status.err:
            return None

        pdf_bytes = result_buffer.getvalue()
        result_buffer.close()
        return pdf_bytes
    except ImportError:
        return None


def send_invoice_email(invoice, attach_pdf=True):
    subject = f"Invoice {invoice.invoice_number} - {invoice.property_name}"
    html_body = render_to_string('invoices/email/reminder_due.html', {'invoice': invoice})

    email = EmailMessage(
        subject=subject,
        body=html_body,
        from_email=django_settings.DEFAULT_FROM_EMAIL,
        to=[invoice.tenant.contact_email],
    )
    email.content_subtype = 'html'

    if attach_pdf:
        pdf = generate_invoice_pdf(invoice)
        if pdf:
            email.attach(f'{invoice.invoice_number}.pdf', pdf, 'application/pdf')

    email.send(fail_silently=False)


def process_reminders():
    today = date.today()
    results = {'upcoming': 0, 'due': 0, 'overdue': 0}

    # 5 days before due
    upcoming = Invoice.objects.filter(
        status__in=['pending'],
        due_date=today + timedelta(days=5),
        reminder_sent_before=False,
    ).select_related('tenant')

    for inv in upcoming:
        try:
            _send_reminder(inv, 'upcoming')
            inv.reminder_sent_before = True
            inv.save(update_fields=['reminder_sent_before'])
            results['upcoming'] += 1
        except Exception:
            pass

    # On due date
    due_today = Invoice.objects.filter(
        status__in=['pending', 'partially_paid'],
        due_date=today,
        reminder_sent_on_due=False,
    ).select_related('tenant')

    for inv in due_today:
        try:
            _send_reminder(inv, 'due')
            inv.reminder_sent_on_due = True
            inv.save(update_fields=['reminder_sent_on_due'])
            results['due'] += 1
        except Exception:
            pass

    # 5 days after due (overdue)
    overdue = Invoice.objects.filter(
        status__in=['pending', 'partially_paid'],
        due_date=today - timedelta(days=5),
        reminder_sent_after=False,
    ).select_related('tenant')

    for inv in overdue:
        try:
            inv.status = Invoice.Status.OVERDUE
            _send_reminder(inv, 'overdue')
            inv.reminder_sent_after = True
            inv.save(update_fields=['status', 'reminder_sent_after'])
            results['overdue'] += 1
        except Exception:
            pass

    return results


def _send_reminder(invoice, reminder_type):
    template_map = {
        'upcoming': 'invoices/email/reminder_upcoming.html',
        'due': 'invoices/email/reminder_due.html',
        'overdue': 'invoices/email/reminder_overdue.html',
    }
    subject_map = {
        'upcoming': f"Upcoming: Invoice {invoice.invoice_number} due on {invoice.due_date.strftime('%d-%b-%Y')}",
        'due': f"Due Today: Invoice {invoice.invoice_number}",
        'overdue': f"OVERDUE: Invoice {invoice.invoice_number} - Payment Required",
    }

    html_body = render_to_string(template_map[reminder_type], {'invoice': invoice})

    email = EmailMessage(
        subject=subject_map[reminder_type],
        body=html_body,
        from_email=django_settings.DEFAULT_FROM_EMAIL,
        to=[invoice.tenant.contact_email],
    )
    email.content_subtype = 'html'

    pdf = generate_invoice_pdf(invoice)
    if pdf:
        email.attach(f'{invoice.invoice_number}.pdf', pdf, 'application/pdf')

    email.send(fail_silently=False)
