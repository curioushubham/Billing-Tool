from django import forms
from datetime import date
from .models import Payment
from properties.models import Property


class GenerateInvoicesForm(forms.Form):
    year = forms.IntegerField(
        initial=date.today().year,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    month = forms.IntegerField(
        initial=date.today().month,
        min_value=1, max_value=12,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 12}),
    )
    properties = forms.ModelMultipleChoiceField(
        queryset=Property.objects.filter(is_active=True),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
        help_text='Leave empty to generate for all properties.',
    )


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'payment_date', 'payment_mode', 'transaction_id', 'remarks']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'payment_mode': forms.Select(attrs={'class': 'form-select'}),
            'transaction_id': forms.TextInput(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class AdjustmentForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=12, decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
    )
    adjustment_type = forms.ChoiceField(
        choices=[('debit', 'Debit (Increase Balance)'), ('credit', 'Credit (Decrease Balance)')],
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    description = forms.CharField(
        max_length=300,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
