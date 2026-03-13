from django.contrib import admin
from .models import Property, Tenant


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'state', 'is_active', 'active_tenants_count']
    list_filter = ['is_active', 'state', 'city']
    search_fields = ['name', 'city']


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'unit_number', 'building', 'rent_amount', 'is_active']
    list_filter = ['is_active', 'billing_cycle', 'building']
    search_fields = ['name', 'company_name', 'unit_number']
