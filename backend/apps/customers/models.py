"""Customers — CustomerProfile + Address (رمزنگاری) + CustomerNote."""
from __future__ import annotations

from django.conf import settings
from django.db import models

from backend.security import decrypt_field, encrypt_field, hmac_sign


class CustomerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="customer_profile")
    default_address = models.ForeignKey("Address", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    loyalty_tier = models.CharField(max_length=30, default="bronze")
    notes = models.TextField(blank=True)
    marketing_opt_in = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "پروفایل مشتری"
        verbose_name_plural = "پروفایل‌های مشتری"

    def __str__(self) -> str:
        return self.user.email


class Address(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addresses")
    title = models.CharField(max_length=60, default="آدرس اصلی")
    recipient_name = models.CharField(max_length=120)
    recipient_phone = models.CharField(max_length=20)
    province = models.CharField(max_length=60)
    city = models.CharField(max_length=60)
    full_address_ciphertext = models.TextField()
    postal_code_hash = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    postal_code_ciphertext = models.TextField(blank=True, null=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "آدرس"
        verbose_name_plural = "آدرس‌ها"
        ordering = ["-is_default", "-created_at"]
        indexes = [models.Index(fields=["user", "is_default"])]

    def __str__(self) -> str:
        return f"{self.recipient_name} — {self.province}/{self.city}"

    @property
    def full_address(self) -> str | None:
        return decrypt_field(self.full_address_ciphertext)

    @full_address.setter
    def full_address(self, value: str) -> None:
        self.full_address_ciphertext = encrypt_field(value)

    @property
    def postal_code(self) -> str | None:
        return decrypt_field(self.postal_code_ciphertext)

    @postal_code.setter
    def postal_code(self, value: str | None) -> None:
        self.postal_code_ciphertext = encrypt_field(value) if value else None
        self.postal_code_hash = hmac_sign(value) if value else None

    def save(self, *args, **kwargs):
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class CustomerNote(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="crm_notes")
    body = models.TextField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "یادداشت مشتری"
        verbose_name_plural = "یادداشت‌های مشتری"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.body[:60]