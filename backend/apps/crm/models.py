"""CRM — Ticket + TicketMessage + Loyalty + Interaction."""
from __future__ import annotations

from django.conf import settings
from django.db import models


class Ticket(models.Model):
    STATUS_OPEN = "open"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = [
        (STATUS_OPEN, "باز"), (STATUS_IN_PROGRESS, "در حال بررسی"), (STATUS_CLOSED, "بسته"),
    ]
    PRIORITY_LOW = "low"
    PRIORITY_NORMAL = "normal"
    PRIORITY_HIGH = "high"
    PRIORITY_CHOICES = [(PRIORITY_LOW, "کم"), (PRIORITY_NORMAL, "عادی"), (PRIORITY_HIGH, "زیاد")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tickets")
    subject = models.CharField(max_length=200)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default=PRIORITY_NORMAL)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_OPEN, db_index=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assigned_tickets", limit_choices_to={"is_staff": True},
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "تیکت"
        verbose_name_plural = "تیکت‌ها"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["status", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"#{self.id} {self.subject}"


class TicketMessage(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    body = models.TextField()
    is_internal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "پیام تیکت"
        verbose_name_plural = "پیام‌های تیکت"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"#{self.ticket_id}: {self.body[:50]}"


class LoyaltyAccount(models.Model):
    TIER_BRONZE = "bronze"
    TIER_SILVER = "silver"
    TIER_GOLD = "gold"
    TIER_CHOICES = [(TIER_BRONZE, "برنز"), (TIER_SILVER, "نقره"), (TIER_GOLD, "طلایی")]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="loyalty")
    points = models.IntegerField(default=0)
    tier = models.CharField(max_length=15, choices=TIER_CHOICES, default=TIER_BRONZE)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "حساب وفاداری"
        verbose_name_plural = "حساب‌های وفاداری"

    def __str__(self) -> str:
        return f"{self.user.email} — {self.points}"


class LoyaltyTransaction(models.Model):
    account = models.ForeignKey(LoyaltyAccount, on_delete=models.CASCADE, related_name="transactions")
    delta = models.IntegerField()
    reason = models.CharField(max_length=100)
    reference = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "تراکنش وفاداری"
        verbose_name_plural = "تراکنش‌های وفاداری"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.delta:+d} — {self.reason}"


class CustomerInteraction(models.Model):
    TYPE_CALL = "call"
    TYPE_EMAIL = "email"
    TYPE_SMS = "sms"
    TYPE_MEETING = "meeting"
    TYPE_NOTE = "note"
    TYPE_CHOICES = [
        (TYPE_CALL, "تماس"), (TYPE_EMAIL, "ایمیل"), (TYPE_SMS, "پیامک"),
        (TYPE_MEETING, "جلسه"), (TYPE_NOTE, "یادداشت"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="interactions")
    kind = models.CharField(max_length=10, choices=TYPE_CHOICES)
    summary = models.TextField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "تعامل مشتری"
        verbose_name_plural = "تعاملات مشتری"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} — {self.user.email}"