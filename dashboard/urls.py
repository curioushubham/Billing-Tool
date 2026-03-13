from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('reports/monthly/', views.report_monthly_view, name='report_monthly'),
    path('reports/outstanding/', views.report_outstanding_view, name='report_outstanding'),
    path('reports/property/', views.report_property_view, name='report_property'),
    path('reports/yearly/', views.report_yearly_view, name='report_yearly'),
    path('reports/export/<str:report_type>/', views.export_report_csv, name='export_report'),
]
