from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.contrib import messages

from .models import User
from .forms import LoginForm, UserCreateForm, UserUpdateForm
from .mixins import AdminRequiredMixin, StaffRequiredMixin


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('login')


class UserListView(AdminRequiredMixin, ListView):
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    paginate_by = 20


class UserCreateView(AdminRequiredMixin, CreateView):
    model = User
    form_class = UserCreateForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('user_list')

    def form_valid(self, form):
        messages.success(self.request, 'User created successfully.')
        return super().form_valid(form)


class UserUpdateView(AdminRequiredMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('user_list')

    def form_valid(self, form):
        messages.success(self.request, 'User updated successfully.')
        return super().form_valid(form)
