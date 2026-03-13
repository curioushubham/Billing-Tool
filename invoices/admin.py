from django.contrib import admin
from .models import Invoice, Payment, TenantLedger


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'tenant_company', 'property_name', 'total_amount', 'balance_due', 'status', 'due_date']
    list_filter = ['status', 'property', 'issue_date']
    search_fields = ['invoice_number', 'tenant_company', 'property_name']
    readonly_fields = ['invoice_number', 'created_at', 'updated_at']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'amount', 'payment_date', 'payment_mode', 'transaction_id']
    list_filter = ['payment_mode', 'payment_date']
    search_fields = ['invoice__invoice_number', 'transaction_id']


@admin.register(TenantLedger)
class TenantLedgerAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'transaction_type', 'debit', 'credit', 'running_balance', 'created_at']
    list_filter = ['transaction_type']
    search_fields = ['tenant__company_name', 'description']
