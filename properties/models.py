from django.db import models
from django.conf import settings


class Property(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    gst_number = models.CharField(max_length=20, blank=True)
    contact_person = models.CharField(max_length=100, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=15, blank=True)
    logo = models.ImageField(upload_to='property_logos/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='properties_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Properties'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def active_tenants_count(self):
        return self.tenants.filter(is_active=True).count()


class Tenant(models.Model):
    class BillingCycle(models.TextChoices):
        MONTHLY = 'monthly', 'Monthly'
        QUARTERLY = 'quarterly', 'Quarterly'

    # Relationship
    building = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name='tenants'
    )

    # Identity
    name = models.CharField(max_length=200)
    company_name = models.CharField(max_length=200)
    unit_number = models.CharField(max_length=50)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=15)
    gst_number = models.CharField(max_length=20, blank=True)

    # Charges
    rent_amount = models.DecimalField(max_digits=12, decimal_places=2)
    maintenance_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    parking_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    electricity_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_charges_description = models.CharField(max_length=200, blank=True)

    # GST & Billing
    gst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=18.00)
    billing_cycle = models.CharField(
        max_length=20, choices=BillingCycle.choices, default=BillingCycle.MONTHLY
    )
    payment_due_day = models.PositiveIntegerField(default=5)
    security_deposit = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Lease
    lease_start_date = models.DateField()
    lease_end_date = models.DateField()

    # Status
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['building', 'unit_number']
        unique_together = ['building', 'unit_number']
        indexes = [
            models.Index(fields=['building', 'is_active']),
        ]

    def __str__(self):
        return f"{self.company_name} - {self.unit_number} ({self.building.name})"

    @property
    def subtotal(self):
        return (
            self.rent_amount + self.maintenance_charges
            + self.parking_charges + self.electricity_charges
            + self.other_charges
        )

    @property
    def gst_amount(self):
        return self.subtotal * self.gst_percentage / 100

    @property
    def total_with_gst(self):
        return self.subtotal + self.gst_amount
