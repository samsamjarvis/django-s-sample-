"""SMS — SMSTemplate + SMSLog + OTPRequest."""
from django.conf import settings
from django.db import models
from django.utils import timezone

from backend.security import decrypt_field, encrypt_field, hmac_sign


class SMSTemplate(models.Model):
    key = models.SlugField(unique=True, max_length=80)
    title = models.CharField(max_length=120)
    body = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "قالب پیامک"
        verbose_name_plural = "قالب‌های پیامک"

    def __str__(self) -> str:
        return f"{self.key} — {self.title}"


class SMSLog(models.Model):
    STATUS_QUEUED = "queued"
    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [(STATUS_QUEUED, "در صف"), (STATUS_SENT, "ارسال‌شده"), (STATUS_FAILED, "ناموفق")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="sms_logs")
    phone_ciphertext = models.TextField()
    phone_hash = models.CharField(max_length=64, db_index=True)
    template_key = models.CharField(max_length=80, blank=True, db_index=True)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_QUEUED, db_index=True)
    provider_message_id = models.CharField(max_length=100, blank=True)
    response_code = models.CharField(max_length=20, blank=True)
    response_data = models.JSONField(default=dict, blank=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "لاگ پیامک"
        verbose_name_plural = "لاگ‌های پیامک"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["phone_hash", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.template_key or 'raw'} → {self.get_status_display()}"

    @property
    def phone(self):
        return decrypt_field(self.phone_ciphertext)

    @phone.setter
    def phone(self, value):
        self.phone_ciphertext = encrypt_field(value)
        self.phone_hash = hmac_sign(value) if value else ""


class OTPRequest(models.Model):
    PURPOSE_LOGIN = "login_2fa"
    PURPOSE_RESET = "password_reset"
    PURPOSE_VERIFY = "phone_verify"
    PURPOSE_CHOICES = [
        (PURPOSE_LOGIN, "ورود 2 مرحله"),
        (PURPOSE_RESET, "بازیابی رمز"),
        (PURPOSE_VERIFY, "تأیید شماره"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sms_otps", null=True, blank=True)
    phone_hash = models.CharField(max_length=64, db_index=True)
    code_hash = models.CharField(max_length=64)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES, db_index=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=5)
    used_at = models.DateTimeField(blank=True, null=True)
    ip = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "درخواست OTP پیامکی"
        verbose_name_plural = "درخواست‌های OTP پیامکی"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["phone_hash", "purpose", "-created_at"])]

    @property
    def is_usable(self) -> bool:
        return (
            self.used_at is None
            and self.attempts < self.max_attempts
            and timezone.now() < self.expires_at
        )