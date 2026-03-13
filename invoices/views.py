import csv
from datetime import date
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.views.generic import ListView, DetailView
from django.contrib import messages
from django.db.models import Q

import openpyxl

from accounts.mixins import StaffRequiredMixin
from .models import Invoice, TenantLedger
from .forms import GenerateInvoicesForm, PaymentForm, AdjustmentForm
from .services import generate_monthly_invoices, generate_invoice_pdf, create_ledger_entry
from properties.models import Tenant


class InvoiceListView(StaffRequiredMixin, ListView):
    model = Invoice
    template_name = 'invoices/invoice_list.html'
    context_object_name = 'invoices'
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(
                Q(invoice_number__icontains=q) | Q(tenant_company__icontains=q)
                | Q(property_name__icontains=q)
            )
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        prop = self.request.GET.get('property')
        if prop:
            qs = qs.filter(property_id=prop)  # Invoice.property FK not renamed
        return qs


class InvoiceDetailView(StaffRequiredMixin, DetailView):
    model = Invoice
    template_name = 'invoices/invoice_detail.html'
    context_object_name = 'invoice'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['payments'] = self.object.payments.all()
        ctx['payment_form'] = PaymentForm(initial={'payment_date': date.today()})
        return ctx


def generate_invoices_view(request):
    if not request.user.is_authenticated or not request.user.is_accountant():
        messages.error(request, 'Permission denied.')
        return redirect('invoice_list')

    if request.method == 'POST':
        form = GenerateInvoicesForm(request.POST)
        if form.is_valid():
            year = form.cleaned_data['year']
            month = form.cleaned_data['month']
            props = form.cleaned_data.get('properties')
            prop_ids = [p.id for p in props] if props else None

            created, skipped = generate_monthly_invoices(
                year, month, property_ids=prop_ids, created_by=request.user
            )
            messages.success(
                request,
                f'Generated {len(created)} invoices. Skipped {len(skipped)} (already exist).'
            )
            return redirect('invoice_list')
    else:
        form = GenerateInvoicesForm()
    return render(request, 'invoices/generate_form.html', {'form': form})


def add_payment_view(request, pk):
    if not request.user.is_authenticated or not request.user.is_accountant():
        messages.error(request, 'Permission denied.')
        return redirect('invoice_list')

    invoice = get_object_or_404(Invoice, pk=pk)

    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.invoice = invoice
            payment.received_by = request.user
            payment.save()
            messages.success(request, f'Payment of {payment.amount} recorded successfully.')
            return redirect('invoice_detail', pk=invoice.pk)
    else:
        form = PaymentForm(initial={'payment_date': date.today()})

    return render(request, 'invoices/payment_form.html', {
        'form': form, 'invoice': invoice,
    })


def invoice_pdf_view(request, pk):
    if not request.user.is_authenticated:
        return redirect('login')
    invoice = get_object_or_404(Invoice, pk=pk)
    pdf = generate_invoice_pdf(invoice)
    if pdf is None:
        messages.error(request, 'PDF generation failed. Ensure xhtml2pdf is installed: pip install xhtml2pdf')
        return redirect('invoice_detail', pk=pk)
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{invoice.invoice_number}.pdf"'
    return response


def cancel_invoice_view(request, pk):
    if not request.user.is_authenticated or request.user.role != 'admin':
        messages.error(request, 'Permission denied.')
        return redirect('invoice_list')

    invoice = get_object_or_404(Invoice, pk=pk)
    if request.method == 'POST':
        invoice.status = Invoice.Status.CANCELLED
        invoice.save(update_fields=['status', 'updated_at'])
        messages.success(request, f'Invoice {invoice.invoice_number} cancelled.')
    return redirect('invoice_detail', pk=pk)


def tenant_ledger_view(request, tenant_pk):
    if not request.user.is_authenticated:
        return redirect('login')

    tenant = get_object_or_404(Tenant, pk=tenant_pk)
    entries = TenantLedger.objects.filter(tenant=tenant).order_by('created_at')

    adjustment_form = AdjustmentForm()

    if request.method == 'POST' and request.user.role == 'admin':
        adjustment_form = AdjustmentForm(request.POST)
        if adjustment_form.is_valid():
            amount = adjustment_form.cleaned_data['amount']
            adj_type = adjustment_form.cleaned_data['adjustment_type']
            desc = adjustment_form.cleaned_data['description']

            debit = amount if adj_type == 'debit' else Decimal('0')
            credit = amount if adj_type == 'credit' else Decimal('0')

            create_ledger_entry(
                tenant=tenant,
                transaction_type='adjustment',
                debit=debit,
                credit=credit,
                description=desc,
                created_by=request.user,
            )
            messages.success(request, 'Adjustment recorded.')
            return redirect('tenant_ledger', tenant_pk=tenant.pk)

    return render(request, 'invoices/ledger.html', {
        'tenant': tenant,
        'entries': entries,
        'adjustment_form': adjustment_form,
    })


def export_invoices_csv(request):
    if not request.user.is_authenticated:
        return redirect('login')

    invoices = Invoice.objects.all().exclude(status='cancelled')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="invoices.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Invoice #', 'Tenant', 'Property', 'Unit', 'Issue Date',
        'Due Date', 'Subtotal', 'GST', 'Total', 'Paid', 'Balance', 'Status'
    ])
    for inv in invoices:
        writer.writerow([
            inv.invoice_number, inv.tenant_company, inv.property_name,
            inv.tenant_unit, inv.issue_date, inv.due_date,
            inv.subtotal, inv.total_gst, inv.total_amount,
            inv.amount_paid, inv.balance_due, inv.get_status_display(),
        ])
    return response


def export_invoices_excel(request):
    if not request.user.is_authenticated:
        return redirect('login')

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Invoices'
    headers = [
        'Invoice #', 'Tenant', 'Property', 'Unit', 'Issue Date',
        'Due Date', 'Subtotal', 'GST', 'Total', 'Paid', 'Balance', 'Status'
    ]
    ws.append(headers)

    for inv in Invoice.objects.all().exclude(status='cancelled'):
        ws.append([
            inv.invoice_number, inv.tenant_company, inv.property_name,
            inv.tenant_unit, str(inv.issue_date), str(inv.due_date),
            float(inv.subtotal), float(inv.total_gst), float(inv.total_amount),
            float(inv.amount_paid), float(inv.balance_due), inv.get_status_display(),
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="invoices.xlsx"'
    wb.save(response)
    return response
