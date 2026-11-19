"""ERP — Supplier + PurchaseOrder + POItem + Expense."""
from django.conf import settings
from django.db import models

from apps.products.models import Product
from backend.security import decrypt_field, encrypt_field


class Supplier(models.Model):
    name = models.CharField(max_length=150)
    contact_name = models.CharField(max_length=120, blank=True)
    phone_ciphertext = models.TextField(blank=True, null=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "تأمین‌کننده"
        verbose_name_plural = "تأمین‌کنندگان"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    @property
    def phone(self):
        return decrypt_field(self.phone_ciphertext)

    @phone.setter
    def phone(self, value):
        self.phone_ciphertext = encrypt_field(value) if value else None


class PurchaseOrder(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_ORDERED = "ordered"
    STATUS_RECEIVED = "received"
    STATUS_CANCELED = "canceled"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "پیش‌نویس"), (STATUS_ORDERED, "ثبت‌شده"),
        (STATUS_RECEIVED, "دریافت‌شده"), (STATUS_CANCELED, "لغو"),
    ]

    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="purchase_orders")
    reference = models.CharField(max_length=30, unique=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)
    total_cost = models.DecimalField(max_digits=14, decimal_places=0, default=0)
    expected_at = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "سفارش خرید"
        verbose_name_plural = "سفارش‌های خرید"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.reference} — {self.supplier.name}"


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="+")
    quantity = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=12, decimal_places=0)

    class Meta:
        verbose_name = "آیتم سفارش خرید"
        verbose_name_plural = "آیتم‌های سفارش خرید"

    @property
    def subtotal(self):
        return self.unit_cost * self.quantity


class Expense(models.Model):
    CATEGORY_RENT = "rent"
    CATEGORY_SALARY = "salary"
    CATEGORY_MARKETING = "marketing"
    CATEGORY_SUPPLIES = "supplies"
    CATEGORY_OTHER = "other"
    CATEGORY_CHOICES = [
        (CATEGORY_RENT, "اجاره"), (CATEGORY_SALARY, "حقوق"),
        (CATEGORY_MARKETING, "بازاریابی"), (CATEGORY_SUPPLIES, "خرید ملزومات"),
        (CATEGORY_OTHER, "سایر"),
    ]

    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    amount = models.DecimalField(max_digits=14, decimal_places=0)
    description = models.CharField(max_length=300)
    paid_at = models.DateField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "هزینه"
        verbose_name_plural = "هزینه‌ها"
        ordering = ["-paid_at"]

    def __str__(self) -> str:
        return f"{self.get_category_display()} — {self.amount}"