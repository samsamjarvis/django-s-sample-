"""Inventory — Stock + StockMovement + Reservation (TTL)."""
from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.products.models import Product


RESERVATION_TTL_MINUTES = 30


class Stock(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="stock")
    quantity = models.PositiveIntegerField(default=0)
    reserved_quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=3)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "موجودی"
        verbose_name_plural = "موجودی‌ها"

    def __str__(self) -> str:
        return f"{self.product.name} — {self.available}"

    @property
    def available(self) -> int:
        return max(self.quantity - self.reserved_quantity, 0)

    @property
    def is_low(self) -> bool:
        return self.available <= self.low_stock_threshold


class StockMovement(models.Model):
    TYPE_IN = "in"
    TYPE_OUT = "out"
    TYPE_ADJUST = "adjust"
    TYPE_RESERVE = "reserve"
    TYPE_RELEASE = "release"
    TYPE_CHOICES = [
        (TYPE_IN, "ورود"), (TYPE_OUT, "خروج"), (TYPE_ADJUST, "اصلاح"),
        (TYPE_RESERVE, "رزرو"), (TYPE_RELEASE, "آزادسازی"),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="stock_movements")
    kind = models.CharField(max_length=10, choices=TYPE_CHOICES)
    quantity = models.IntegerField()
    reason = models.CharField(max_length=200, blank=True)
    reference = models.CharField(max_length=100, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "تراکنش انبار"
        verbose_name_plural = "تراکنش‌های انبار"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["product", "-created_at"]),
            models.Index(fields=["reference"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} {self.quantity} {self.product.name}"


class Reservation(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_CONSUMED = "consumed"
    STATUS_RELEASED = "released"
    STATUS_EXPIRED = "expired"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "فعال"), (STATUS_CONSUMED, "تبدیل‌شده به سفارش"),
        (STATUS_RELEASED, "آزادشده"), (STATUS_EXPIRED, "منقضی"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reservations", null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reservations")
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_ACTIVE, db_index=True)
    expires_at = models.DateTimeField()
    order_reference = models.CharField(max_length=100, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "رزرو موجودی"
        verbose_name_plural = "رزروهای موجودی"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "expires_at"]),
            models.Index(fields=["user", "status"]),
            models.Index(fields=["product", "status"]),
            models.Index(fields=["status", "expires_at", "product"]),
        ]

    def __str__(self) -> str:
        return f"#{self.id} {self.product.name} × {self.quantity} ({self.status})"

    @property
    def is_expired(self) -> bool:
        return self.status == self.STATUS_ACTIVE and timezone.now() >= self.expires_at

    @classmethod
    def default_expiry(cls):
        return timezone.now() + timedelta(minutes=RESERVATION_TTL_MINUTES)