from django.urls import path
from . import views

urlpatterns = [
    path('', views.InvoiceListView.as_view(), name='invoice_list'),
    path('generate/', views.generate_invoices_view, name='generate_invoices'),
    path('<int:pk>/', views.InvoiceDetailView.as_view(), name='invoice_detail'),
    path('<int:pk>/pdf/', views.invoice_pdf_view, name='invoice_pdf'),
    path('<int:pk>/payment/', views.add_payment_view, name='add_payment'),
    path('<int:pk>/cancel/', views.cancel_invoice_view, name='cancel_invoice'),
    path('ledger/<int:tenant_pk>/', views.tenant_ledger_view, name='tenant_ledger'),
    path('export/csv/', views.export_invoices_csv, name='export_csv'),
    path('export/excel/', views.export_invoices_excel, name='export_excel'),
]
