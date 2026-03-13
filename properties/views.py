from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q

from accounts.mixins import AdminRequiredMixin, AccountantRequiredMixin, StaffRequiredMixin
from .models import Property, Tenant
from .forms import PropertyForm, TenantForm, BulkImportForm
from .services import import_tenants_from_excel


# --- Property Views ---

class PropertyListView(StaffRequiredMixin, ListView):
    model = Property
    template_name = 'properties/property_list.html'
    context_object_name = 'properties'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(city__icontains=q))
        return qs


class PropertyCreateView(AdminRequiredMixin, CreateView):
    model = Property
    form_class = PropertyForm
    template_name = 'properties/property_form.html'
    success_url = reverse_lazy('property_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Property created successfully.')
        return super().form_valid(form)


class PropertyUpdateView(AdminRequiredMixin, UpdateView):
    model = Property
    form_class = PropertyForm
    template_name = 'properties/property_form.html'
    success_url = reverse_lazy('property_list')

    def form_valid(self, form):
        messages.success(self.request, 'Property updated successfully.')
        return super().form_valid(form)


class PropertyDetailView(StaffRequiredMixin, DetailView):
    model = Property
    template_name = 'properties/property_detail.html'
    context_object_name = 'property'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['tenants'] = self.object.tenants.filter(is_active=True)
        return ctx


class PropertyDeleteView(AdminRequiredMixin, DeleteView):
    model = Property
    template_name = 'properties/property_confirm_delete.html'
    success_url = reverse_lazy('property_list')

    def form_valid(self, form):
        messages.success(self.request, 'Property deleted successfully.')
        return super().form_valid(form)


# --- Tenant Views ---

class TenantListView(StaffRequiredMixin, ListView):
    model = Tenant
    template_name = 'properties/tenant_list.html'
    context_object_name = 'tenants'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('building')
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(
                Q(name__icontains=q) | Q(company_name__icontains=q)
                | Q(unit_number__icontains=q) | Q(building__name__icontains=q)
            )
        prop = self.request.GET.get('property')
        if prop:
            qs = qs.filter(building_id=prop)
        status = self.request.GET.get('status')
        if status == 'active':
            qs = qs.filter(is_active=True)
        elif status == 'inactive':
            qs = qs.filter(is_active=False)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['properties'] = Property.objects.filter(is_active=True)
        return ctx


class TenantCreateView(AccountantRequiredMixin, CreateView):
    model = Tenant
    form_class = TenantForm
    template_name = 'properties/tenant_form.html'
    success_url = reverse_lazy('tenant_list')

    def form_valid(self, form):
        messages.success(self.request, 'Tenant created successfully.')
        return super().form_valid(form)


class TenantUpdateView(AccountantRequiredMixin, UpdateView):
    model = Tenant
    form_class = TenantForm
    template_name = 'properties/tenant_form.html'
    success_url = reverse_lazy('tenant_list')

    def form_valid(self, form):
        messages.success(self.request, 'Tenant updated successfully.')
        return super().form_valid(form)


class TenantDetailView(StaffRequiredMixin, DetailView):
    model = Tenant
    template_name = 'properties/tenant_detail.html'
    context_object_name = 'tenant'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['invoices'] = self.object.invoices.all()[:20]
        ctx['ledger'] = self.object.ledger_entries.all()[:30]
        return ctx


class TenantDeleteView(AdminRequiredMixin, DeleteView):
    model = Tenant
    template_name = 'properties/tenant_confirm_delete.html'
    success_url = reverse_lazy('tenant_list')

    def form_valid(self, form):
        messages.success(self.request, 'Tenant deleted successfully.')
        return super().form_valid(form)


# --- Bulk Import ---

def tenant_import_view(request):
    if not request.user.is_authenticated or request.user.role != 'admin':
        messages.error(request, 'You do not have permission to import tenants.')
        return redirect('tenant_list')

    if request.method == 'POST':
        form = BulkImportForm(request.POST, request.FILES)
        if form.is_valid():
            created, errors = import_tenants_from_excel(request.FILES['file'])
            if created:
                messages.success(request, f'{len(created)} tenants imported successfully.')
            if errors:
                for err in errors[:10]:
                    messages.warning(request, f"Row {err['row']}: {err['message']}")
                if len(errors) > 10:
                    messages.warning(request, f'... and {len(errors) - 10} more errors.')
            return redirect('tenant_list')
    else:
        form = BulkImportForm()
    return render(request, 'properties/tenant_import.html', {'form': form})
