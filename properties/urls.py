from django.urls import path
from . import views

urlpatterns = [
    # Properties
    path('', views.PropertyListView.as_view(), name='property_list'),
    path('create/', views.PropertyCreateView.as_view(), name='property_create'),
    path('<int:pk>/', views.PropertyDetailView.as_view(), name='property_detail'),
    path('<int:pk>/edit/', views.PropertyUpdateView.as_view(), name='property_update'),
    path('<int:pk>/delete/', views.PropertyDeleteView.as_view(), name='property_delete'),
    # Tenants
    path('tenants/', views.TenantListView.as_view(), name='tenant_list'),
    path('tenants/create/', views.TenantCreateView.as_view(), name='tenant_create'),
    path('tenants/<int:pk>/', views.TenantDetailView.as_view(), name='tenant_detail'),
    path('tenants/<int:pk>/edit/', views.TenantUpdateView.as_view(), name='tenant_update'),
    path('tenants/<int:pk>/delete/', views.TenantDeleteView.as_view(), name='tenant_delete'),
    path('tenants/import/', views.tenant_import_view, name='tenant_import'),
]
