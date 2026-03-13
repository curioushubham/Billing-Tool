from datetime import date
from django.db import models
from django.conf import settings
from properties.models import Tenant, Property


class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PENDING = 'pending', 'Pending'
        PAID = 'paid', 'Paid'
        PARTIALLY_PAID = 'partially_paid', 'Partially Paid'
        OVERDUE = 'overdue', 'Overdue'
        CANCELLED = 'cancelled', 'Cancelled'

    # Identity
    invoice_number = models.CharField(max_length=50, unique=True, db_index=True)

    # Relationships
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='invoices')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='invoices')

    # Dates
    billing_period_start = models.DateField()
    billing_period_end = models.DateField()
    issue_date = models.DateField()
    due_date = models.DateField()

    # Snapshot of charges
    rent_amount = models.DecimalField(max_digits=12, decimal_places=2)
    maintenance_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    parking_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    electricity_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_charges_description = models.CharField(max_length=200, blank=True)

    # GST
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    gst_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    cgst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sgst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    igst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_gst = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)

    # Payment tracking
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    balance_due = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    # Tenant/property snapshot for historical record
    tenant_name = models.CharField(max_length=200)
    tenant_company = models.CharField(max_length=200)
    tenant_gst = models.CharField(max_length=20, blank=True)
    tenant_unit = models.CharField(max_length=50)
    property_name = models.CharField(max_length=200)
    property_address = models.TextField()
    property_gst = models.CharField(max_length=20, blank=True)

    # Reminders
    reminder_sent_before = models.BooleanField(default=False)
    reminder_sent_on_due = models.BooleanField(default=False)
    reminder_sent_after = models.BooleanField(default=False)

    # Meta
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-issue_date', '-invoice_number']
        indexes = [
            models.Index(fields=['status', 'due_date']),
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['property', 'issue_date']),
            models.Index(fields=['issue_date']),
            models.Index(fields=['billing_period_start', 'tenant']),
        ]

    def __str__(self):
        return f"{self.invoice_number} - {self.tenant_company}"

    def update_payment_status(self):
        total_paid = self.payments.aggregate(total=models.Sum('amount'))['total'] or 0
        self.amount_paid = total_paid
        self.balance_due = self.total_amount - total_paid

        if total_paid >= self.total_amount:
            self.status = self.Status.PAID
        elif total_paid > 0:
            self.status = self.Status.PARTIALLY_PAID
        elif self.due_date < date.today():
            self.status = self.Status.OVERDUE
        else:
            self.status = self.Status.PENDING
        self.save(update_fields=['amount_paid', 'balance_due', 'status', 'updated_at'])


class Payment(models.Model):
    class Mode(models.TextChoices):
        CASH = 'cash', 'Cash'
        CHEQUE = 'cheque', 'Cheque'
        BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
        UPI = 'upi', 'UPI'
        ONLINE = 'online', 'Online'
        OTHER = 'other', 'Other'

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField()
    payment_mode = models.CharField(max_length=20, choices=Mode.choices)
    transaction_id = models.CharField(max_length=100, blank=True)
    remarks = models.TextField(blank=True)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-payment_date']

    def __str__(self):
        return f"Payment of {self.amount} for {self.invoice.invoice_number}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        self.invoice.update_payment_status()
        if is_new:
            from .services import create_ledger_entry
            create_ledger_entry(
                tenant=self.invoice.tenant,
                payment=self,
                invoice=self.invoice,
                transaction_type='payment',
                credit=self.amount,
                description=f"Payment received for {self.invoice.invoice_number} via {self.get_payment_mode_display()}",
                created_by=self.received_by,
            )


class TenantLedger(models.Model):
    class TransactionType(models.TextChoices):
        INVOICE = 'invoice', 'Invoice'
        PAYMENT = 'payment', 'Payment'
        ADJUSTMENT = 'adjustment', 'Adjustment'

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='ledger_entries')
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True)
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True)
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    debit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    running_balance = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['tenant', 'created_at']),
            models.Index(fields=['transaction_type', 'created_at']),
        ]

    def __str__(self):
        return f"{self.tenant} - {self.transaction_type} - {self.debit or self.credit}"
