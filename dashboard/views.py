import csv
from datetime import date, timedelta
from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Sum, Count, Q
from django.contrib.auth.decorators import login_required
from invoices.models import Invoice, Payment
from properties.models import Property, Tenant


@login_required
def dashboard_view(request):
    today = date.today()
    current_month = today.month
    current_year = today.year

    month_invoices = Invoice.objects.filter(
        issue_date__year=current_year,
        issue_date__month=current_month,
    ).exclude(status='cancelled')

    total_billed = month_invoices.aggregate(t=Sum('total_amount'))['t'] or 0
    total_collected = month_invoices.aggregate(t=Sum('amount_paid'))['t'] or 0
    pending_amount = month_invoices.filter(
        status__in=['pending', 'partially_paid']
    ).aggregate(t=Sum('balance_due'))['t'] or 0
    overdue_amount = month_invoices.filter(
        status='overdue'
    ).aggregate(t=Sum('balance_due'))['t'] or 0

    active_tenants = Tenant.objects.filter(is_active=True).count()
    active_properties = Property.objects.filter(is_active=True).count()

    overdue_invoices = Invoice.objects.filter(status='overdue').order_by('-due_date')[:10]

    week_end = today + timedelta(days=7)
    due_this_week = Invoice.objects.filter(
        status__in=['pending', 'partially_paid'],
        due_date__gte=today,
        due_date__lte=week_end,
    ).order_by('due_date')[:10]

    recent_payments = Payment.objects.select_related('invoice').order_by('-created_at')[:10]

    property_revenue = list(month_invoices.values('property__name').annotate(
        total=Sum('total_amount'), collected=Sum('amount_paid'),
    ).order_by('-total'))

    monthly_trend = []
    for i in range(11, -1, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        agg = Invoice.objects.filter(
            issue_date__year=y, issue_date__month=m,
        ).exclude(status='cancelled').aggregate(
            t=Sum('total_amount'), c=Sum('amount_paid'),
        )
        monthly_trend.append({
            'month': date(y, m, 1).strftime('%b %Y'),
            'billed': float(agg['t'] or 0),
            'collected': float(agg['c'] or 0),
        })

    return render(request, 'dashboard/index.html', {
        'total_billed': total_billed,
        'total_collected': total_collected,
        'pending_amount': pending_amount,
        'overdue_amount': overdue_amount,
        'active_tenants': active_tenants,
        'active_properties': active_properties,
        'overdue_invoices': overdue_invoices,
        'due_this_week': due_this_week,
        'recent_payments': recent_payments,
        'property_revenue': property_revenue,
        'monthly_trend': monthly_trend,
    })


@login_required
def report_monthly_view(request):
    year = int(request.GET.get('year', date.today().year))
    month = int(request.GET.get('month', date.today().month))

    invoices = Invoice.objects.filter(
        issue_date__year=year, issue_date__month=month,
    ).exclude(status='cancelled').order_by('property_name', 'tenant_company')

    totals = invoices.aggregate(
        total_billed=Sum('total_amount'),
        total_paid=Sum('amount_paid'),
        total_balance=Sum('balance_due'),
    )

    return render(request, 'dashboard/report_monthly.html', {
        'invoices': invoices, 'totals': totals,
        'year': year, 'month': month,
        'month_name': date(year, month, 1).strftime('%B %Y'),
    })


@login_required
def report_outstanding_view(request):
    tenants = Tenant.objects.filter(
        is_active=True,
        invoices__status__in=['pending', 'partially_paid', 'overdue'],
    ).annotate(
        total_outstanding=Sum('invoices__balance_due', filter=Q(
            invoices__status__in=['pending', 'partially_paid', 'overdue']
        )),
        overdue_count=Count('invoices', filter=Q(invoices__status='overdue')),
    ).filter(total_outstanding__gt=0).select_related('building').order_by('-total_outstanding')

    return render(request, 'dashboard/report_outstanding.html', {'tenants': tenants})


@login_required
def report_property_view(request):
    year = int(request.GET.get('year', date.today().year))

    properties = Property.objects.filter(is_active=True).annotate(
        total_billed=Sum('invoices__total_amount', filter=Q(
            invoices__issue_date__year=year) & ~Q(invoices__status='cancelled')),
        total_collected=Sum('invoices__amount_paid', filter=Q(
            invoices__issue_date__year=year) & ~Q(invoices__status='cancelled')),
    ).order_by('-total_billed')

    return render(request, 'dashboard/report_property.html', {
        'properties': properties, 'year': year,
    })


@login_required
def report_yearly_view(request):
    year = int(request.GET.get('year', date.today().year))

    monthly_data = []
    for m in range(1, 13):
        data = Invoice.objects.filter(
            issue_date__year=year, issue_date__month=m,
        ).exclude(status='cancelled').aggregate(
            billed=Sum('total_amount'), collected=Sum('amount_paid'),
        )
        monthly_data.append({
            'month': date(year, m, 1).strftime('%B'),
            'billed': data['billed'] or 0,
            'collected': data['collected'] or 0,
            'outstanding': (data['billed'] or 0) - (data['collected'] or 0),
        })

    yearly_total = Invoice.objects.filter(
        issue_date__year=year,
    ).exclude(status='cancelled').aggregate(
        billed=Sum('total_amount'), collected=Sum('amount_paid'),
    )

    return render(request, 'dashboard/report_yearly.html', {
        'monthly_data': monthly_data, 'yearly_total': yearly_total, 'year': year,
    })


@login_required
def export_report_csv(request, report_type):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{report_type}_report.csv"'
    writer = csv.writer(response)

    if report_type == 'monthly':
        year = int(request.GET.get('year', date.today().year))
        month = int(request.GET.get('month', date.today().month))
        writer.writerow(['Invoice #', 'Tenant', 'Property', 'Total', 'Paid', 'Balance', 'Status'])
        for inv in Invoice.objects.filter(
            issue_date__year=year, issue_date__month=month
        ).exclude(status='cancelled'):
            writer.writerow([
                inv.invoice_number, inv.tenant_company, inv.property_name,
                inv.total_amount, inv.amount_paid, inv.balance_due, inv.get_status_display(),
            ])
    elif report_type == 'outstanding':
        writer.writerow(['Tenant', 'Property', 'Unit', 'Outstanding', 'Overdue Count'])
        tenants = Tenant.objects.filter(
            is_active=True, invoices__status__in=['pending', 'partially_paid', 'overdue'],
        ).annotate(
            total_outstanding=Sum('invoices__balance_due', filter=Q(
                invoices__status__in=['pending', 'partially_paid', 'overdue'])),
            overdue_count=Count('invoices', filter=Q(invoices__status='overdue')),
        ).filter(total_outstanding__gt=0).select_related('building')
        for t in tenants:
            writer.writerow([t.company_name, t.building.name, t.unit_number, t.total_outstanding, t.overdue_count])

    return response
