"""UserManager — ایجاد با ایمیل + جستجوی امن با phone_hash."""
from __future__ import annotations

from typing import Optional

from django.contrib.auth.base_user import BaseUserManager

from backend.security import hmac_sign


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email: str, password: Optional[str], **extra):
        if not email:
            raise ValueError("ایمیل الزامی است.")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: Optional[str] = None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email: str, password: str, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("is_active", True)
        extra.setdefault("is_customer", False)
        return self._create_user(email, password, **extra)

    def find_by_phone(self, phone: str):
        if not phone:
            return self.none()
        return self.filter(phone_hash=hmac_sign(phone))

    def active_customers(self):
        return self.filter(is_active=True, is_customer=True)