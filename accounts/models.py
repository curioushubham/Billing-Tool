from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        ACCOUNTANT = 'accountant', 'Accountant'
        VIEWER = 'viewer', 'Viewer'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.VIEWER)
    phone = models.CharField(max_length=15, blank=True)

    def is_admin_user(self):
        return self.role == self.Role.ADMIN

    def is_accountant(self):
        return self.role in (self.Role.ADMIN, self.Role.ACCOUNTANT)

    def is_viewer_only(self):
        return self.role == self.Role.VIEWER
