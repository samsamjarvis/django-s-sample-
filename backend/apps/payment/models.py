"""Payment — Payment + PaymentAttempt."""
from __future__ import annotations

from django.db import models

from apps.orders.models import Order


class Payment(models.Model):
    GATEWAY_ZARINPAL = "zarinpal"
    GATEWAY_CHOICES = [(GATEWAY_ZARINPAL, "زرین‌پال")]

    STATUS_INITIATED = "initiated"
    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_FAILED = "failed"
    STATUS_CANCELED = "canceled"
    STATUS_REFUNDED = "refunded"
    STATUS_CHOICES = [
        (STATUS_INITIATED, "ایجاد‌شده"),
        (STATUS_PENDING, "در انتظار"),
        (STATUS_PAID, "پرداخت‌شده"),
        (STATUS_FAILED, "ناموفق"),
        (STATUS_CANCELED, "لغو"),
        (STATUS_REFUNDED, "بازپرداخت"),
    ]

    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="payments")
    gateway = models.CharField(max_length=20, choices=GATEWAY_CHOICES, default=GATEWAY_ZARINPAL)
    amount = models.DecimalField(max_digits=12, decimal_places=0)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_INITIATED, db_index=True)
    authority = models.CharField(max_length=100, blank=True, db_index=True)
    ref_id = models.CharField(max_length=100, blank=True, db_index=True)
    card_pan = models.CharField(max_length=30, blank=True)
    raw_response = models.JSONField(default=dict, blank=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "پرداخت"
        verbose_name_plural = "پرداخت‌ها"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order", "status"]),
            models.Index(fields=["authority"]),
        ]

    def __str__(self) -> str:
        return f"#{self.id} {self.order.order_number} — {self.get_status_display()}"


class PaymentAttempt(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="attempts")
    status = models.CharField(max_length=20)
    code = models.CharField(max_length=20, blank=True)
    message = models.CharField(max_length=300, blank=True)
    response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "تلاش پرداخت"
        verbose_name_plural = "تلاش‌های پرداخت"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.payment_id} — {self.status}"