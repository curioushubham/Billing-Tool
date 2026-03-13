from django import forms
from .models import Property, Tenant


class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = [
            'name', 'address', 'city', 'state', 'pincode',
            'gst_number', 'contact_person', 'contact_email',
            'contact_phone', 'logo', 'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control'}),
            'gst_number': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'logo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class TenantForm(forms.ModelForm):
    class Meta:
        model = Tenant
        fields = [
            'building', 'name', 'company_name', 'unit_number',
            'contact_email', 'contact_phone', 'gst_number',
            'rent_amount', 'maintenance_charges', 'parking_charges',
            'electricity_charges', 'other_charges', 'other_charges_description',
            'gst_percentage', 'billing_cycle', 'payment_due_day',
            'security_deposit', 'lease_start_date', 'lease_end_date',
            'is_active', 'notes',
        ]
        widgets = {
            'building': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'unit_number': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'gst_number': forms.TextInput(attrs={'class': 'form-control'}),
            'rent_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'maintenance_charges': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'parking_charges': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'electricity_charges': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'other_charges': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'other_charges_description': forms.TextInput(attrs={'class': 'form-control'}),
            'gst_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'billing_cycle': forms.Select(attrs={'class': 'form-select'}),
            'payment_due_day': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 28}),
            'security_deposit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'lease_start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'lease_end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class BulkImportForm(forms.Form):
    file = forms.FileField(
        label='Excel File (.xlsx)',
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.xlsx'}),
    )
