"""Orders — Cart + CartItem + Order + OrderItem + OrderStatusHistory."""
from __future__ import annotations

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.products.models import Product


def _new_order_number() -> str:
    return timezone.now().strftime("%y%m%d") + uuid.uuid4().hex[:8].upper()


class Cart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="carts", null=True, blank=True)
    session_key = models.CharField(max_length=64, blank=True, db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "سبد خرید"
        verbose_name_plural = "سبدهای خرید"
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["session_key", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"Cart#{self.id} ({'user' if self.user_id else 'guest'})"

    @property
    def total_quantity(self) -> int:
        return sum(item.quantity for item in self.items.all())

    @property
    def total_amount(self) -> Decimal:
        return sum((item.subtotal for item in self.items.all()), Decimal("0"))


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="+")
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=0)
    reservation = models.ForeignKey("inventory.Reservation", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "آیتم سبد"
        verbose_name_plural = "آیتم‌های سبد"
        unique_together = [("cart", "product")]
        indexes = [
            models.Index(fields=["cart"]),
            models.Index(fields=["cart", "product"]),
        ]

    def __str__(self) -> str:
        return f"{self.product.name} × {self.quantity}"

    @property
    def subtotal(self) -> Decimal:
        return Decimal(self.unit_price) * self.quantity


class Order(models.Model):
    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_PROCESSING = "processing"
    STATUS_SHIPPED = "shipped"
    STATUS_DELIVERED = "delivered"
    STATUS_CANCELED = "canceled"
    STATUS_REFUNDED = "refunded"
    STATUS_CHOICES = [
        (STATUS_PENDING, "در انتظار پرداخت"),
        (STATUS_PAID, "پرداخت‌شده"),
        (STATUS_PROCESSING, "در حال آماده‌سازی"),
        (STATUS_SHIPPED, "ارسال‌شده"),
        (STATUS_DELIVERED, "تحویل‌شده"),
        (STATUS_CANCELED, "لغو‌شده"),
        (STATUS_REFUNDED, "بازپرداخت"),
    ]

    PAYMENT_UNPAID = "unpaid"
    PAYMENT_PAID = "paid"
    PAYMENT_FAILED = "failed"
    PAYMENT_REFUNDED = "refunded"
    PAYMENT_CHOICES = [
        (PAYMENT_UNPAID, "پرداخت‌نشده"),
        (PAYMENT_PAID, "پرداخت‌شده"),
        (PAYMENT_FAILED, "ناموفق"),
        (PAYMENT_REFUNDED, "بازپرداخت"),
    ]

    order_number = models.CharField(max_length=30, unique=True, default=_new_order_number, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    payment_status = models.CharField(max_length=15, choices=PAYMENT_CHOICES, default=PAYMENT_UNPAID, db_index=True)

    subtotal_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    shipping_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0)

    shipping_full_name = models.CharField(max_length=150)
    shipping_phone = models.CharField(max_length=20)
    shipping_province = models.CharField(max_length=60)
    shipping_city = models.CharField(max_length=60)
    shipping_address = models.TextField()
    shipping_postal_code = models.CharField(max_length=20, blank=True)

    customer_note = models.TextField(blank=True)
    admin_note = models.TextField(blank=True)

    paid_at = models.DateTimeField(blank=True, null=True)
    shipped_at = models.DateTimeField(blank=True, null=True)
    delivered_at = models.DateTimeField(blank=True, null=True)
    canceled_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "سفارش"
        verbose_name_plural = "سفارش‌ها"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["payment_status"]),
            models.Index(fields=["payment_status", "-paid_at"]),
            models.Index(fields=["-created_at", "status"]),
            models.Index(fields=["order_number"]),
        ]

    def __str__(self) -> str:
        return f"#{self.order_number}"

    @property
    def is_paid(self) -> bool:
        return self.payment_status == self.PAYMENT_PAID

    @property
    def is_cancelable(self) -> bool:
        return self.status in (self.STATUS_PENDING, self.STATUS_PAID) and not self.shipped_at


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="+")
    product_name = models.CharField(max_length=200)
    product_image_path = models.CharField(max_length=300, blank=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=0)
    quantity = models.PositiveIntegerField()

    class Meta:
        verbose_name = "آیتم سفارش"
        verbose_name_plural = "آیتم‌های سفارش"
        indexes = [models.Index(fields=["order"])]

    def __str__(self) -> str:
        return f"{self.product_name} × {self.quantity}"

    @property
    def subtotal(self) -> Decimal:
        return Decimal(self.unit_price) * self.quantity


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    note = models.CharField(max_length=300, blank=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "تاریخچه وضعیت سفارش"
        verbose_name_plural = "تاریخچه وضعیت سفارش‌ها"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.order.order_number}: {self.from_status} → {self.to_status}"