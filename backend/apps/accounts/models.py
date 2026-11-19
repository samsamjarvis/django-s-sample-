"""
Accounts — مدل کاربر سفارشی (AUTH_USER_MODEL) + OTP + RecoveryCode + SecurityEvent.
رمزنگاری فیلدهای حساس با Fernet + HMAC indexed برای جستجو.
public_id (UUID) → پایداری CRM در تغییر اطلاعات.
"""
from __future__ import annotations

import secrets
import uuid
from datetime import timedelta

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from backend.security import decrypt_field, encrypt_field, hmac_sign
from .managers import UserManager


def user_avatar_path(instance: "User", filename: str) -> str:
    return f"avatars/{instance.public_id}/{filename}"


class User(AbstractBaseUser, PermissionsMixin):
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=80, blank=True)
    last_name = models.CharField(max_length=80, blank=True)

    phone_ciphertext = models.TextField(blank=True, null=True)
    phone_hash = models.CharField(
        max_length=64, unique=True, null=True, blank=True, db_index=True,
        validators=[RegexValidator(r"^[a-f0-9]{64}$")],
    )

    national_id_ciphertext = models.TextField(blank=True, null=True)
    national_id_hash = models.CharField(max_length=64, null=True, blank=True, db_index=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_customer = models.BooleanField(default=True)

    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret_ciphertext = models.TextField(blank=True, null=True)
    two_factor_confirmed_at = models.DateTimeField(blank=True, null=True)

    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    last_login_user_agent = models.CharField(max_length=300, blank=True)

    avatar = models.ImageField(upload_to=user_avatar_path, blank=True, null=True)

    date_joined = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    password_changed_at = models.DateTimeField(blank=True, null=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []
    EMAIL_FIELD = "email"

    objects = UserManager()

    class Meta:
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"
        indexes = [
            models.Index(fields=["is_active", "is_customer"]),
            models.Index(fields=["is_staff"]),
        ]

    def __str__(self) -> str:
        return self.email

    @property
    def phone(self) -> str | None:
        return decrypt_field(self.phone_ciphertext)

    @phone.setter
    def phone(self, value: str | None) -> None:
        self.phone_ciphertext = encrypt_field(value) if value else None
        self.phone_hash = hmac_sign(value) if value else None

    @property
    def national_id(self) -> str | None:
        return decrypt_field(self.national_id_ciphertext)

    @national_id.setter
    def national_id(self, value: str | None) -> None:
        self.national_id_ciphertext = encrypt_field(value) if value else None
        self.national_id_hash = hmac_sign(value) if value else None

    @property
    def two_factor_secret(self) -> str | None:
        return decrypt_field(self.two_factor_secret_ciphertext)

    @two_factor_secret.setter
    def two_factor_secret(self, value: str | None) -> None:
        self.two_factor_secret_ciphertext = encrypt_field(value) if value else None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.email

    def get_short_name(self) -> str:
        return self.first_name or self.email.split("@")[0]


class TwoFactorOTP(models.Model):
    PURPOSE_LOGIN = "login_2fa"
    PURPOSE_RESET = "password_reset"
    PURPOSE_VERIFY = "phone_verify"
    PURPOSE_CHOICES = [
        (PURPOSE_LOGIN, "ورود دو مرحله‌ای"),
        (PURPOSE_RESET, "بازیابی رمز"),
        (PURPOSE_VERIFY, "تأیید شماره"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otp_codes", null=True, blank=True)
    phone_hash = models.CharField(max_length=64, db_index=True)
    code_hash = models.CharField(max_length=64, db_index=True)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=5)
    used_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField(blank=True, null=True)

    class Meta:
        verbose_name = "کد یکبارمصرف"
        verbose_name_plural = "کدهای یکبارمصرف"
        indexes = [models.Index(fields=["phone_hash", "purpose", "used_at"])]

    def __str__(self) -> str:
        return f"OTP({self.purpose}) {self.created_at:%Y-%m-%d %H:%M}"

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    @property
    def is_usable(self) -> bool:
        return self.used_at is None and not self.is_expired and self.attempts < self.max_attempts

    @classmethod
    def default_expiry(cls):
        return timezone.now() + timedelta(minutes=2)


class RecoveryCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recovery_codes")
    code_hash = models.CharField(max_length=64, db_index=True)
    used_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "کد بازیابی"
        verbose_name_plural = "کدهای بازیابی"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "used_at"])]

    def __str__(self) -> str:
        return f"recovery#{self.id} used={bool(self.used_at)}"

    @staticmethod
    def generate_code() -> str:
        return f"{secrets.token_hex(2)}-{secrets.token_hex(2)}"


class SecurityEvent(models.Model):
    TYPE_LOGIN_SUCCESS = "login_success"
    TYPE_LOGIN_FAILED = "login_failed"
    TYPE_LOGOUT = "logout"
    TYPE_LOCKOUT = "lockout"
    TYPE_2FA_SUCCESS = "2fa_success"
    TYPE_2FA_FAILED = "2fa_failed"
    TYPE_2FA_ENABLED = "2fa_enabled"
    TYPE_2FA_DISABLED = "2fa_disabled"
    TYPE_PASSWORD_CHANGED = "password_changed"
    TYPE_PASSWORD_RESET = "password_reset"
    TYPE_RECOVERY_CODE_USED = "recovery_code_used"
    TYPE_SESSION_INVALIDATED = "session_invalidated"
    TYPE_SUSPICIOUS_IP = "suspicious_ip"

    TYPE_CHOICES = [
        (TYPE_LOGIN_SUCCESS, "ورود موفق"),
        (TYPE_LOGIN_FAILED, "ورود ناموفق"),
        (TYPE_LOGOUT, "خروج"),
        (TYPE_LOCKOUT, "قفل حساب"),
        (TYPE_2FA_SUCCESS, "تأیید دو مرحله‌ای موفق"),
        (TYPE_2FA_FAILED, "تأیید دو مرحله‌ای ناموفق"),
        (TYPE_2FA_ENABLED, "فعال‌سازی دو مرحله‌ای"),
        (TYPE_2FA_DISABLED, "غیرفعال‌سازی دو مرحله‌ای"),
        (TYPE_PASSWORD_CHANGED, "تغییر رمز"),
        (TYPE_PASSWORD_RESET, "بازیابی رمز"),
        (TYPE_RECOVERY_CODE_USED, "استفاده از کد بازیابی"),
        (TYPE_SESSION_INVALIDATED, "باطل‌سازی نشست"),
        (TYPE_SUSPICIOUS_IP, "IP مشکوک"),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="security_events")
    event_type = models.CharField(max_length=30, choices=TYPE_CHOICES, db_index=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    email_attempted = models.CharField(max_length=254, blank=True)
    detail = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "رویداد امنیتی"
        verbose_name_plural = "رویدادهای امنیتی"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_type", "-created_at"]),
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["ip", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_event_type_display()} @ {self.created_at:%Y-%m-%d %H:%M}"