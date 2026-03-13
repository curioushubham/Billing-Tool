from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class StaffRequiredMixin(LoginRequiredMixin):
    """All logged-in users can access."""
    pass


class AccountantRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Admin and Accountant can access."""
    def test_func(self):
        return self.request.user.role in ('admin', 'accountant')


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Only Admin can access."""
    def test_func(self):
        return self.request.user.role == 'admin'
