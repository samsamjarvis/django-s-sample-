"""Dashboard — AuditLog + AdminNotification."""
from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    action = models.CharField(max_length=30, db_index=True)
    model_name = models.CharField(max_length=80, blank=True)
    object_id = models.CharField(max_length=64, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "لاگ حسابرسی"
        verbose_name_plural = "لاگ‌های حسابرسی"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["action", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.action} — {self.model_name}#{self.object_id}"


class AdminNotification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="admin_notifications",
        limit_choices_to={"is_staff": True},
    )
    title = models.CharField(max_length=150)
    message = models.TextField(blank=True)
    url = models.CharField(max_length=300, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "اعلان ادمین"
        verbose_name_plural = "اعلان‌های ادمین"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "is_read", "-created_at"])]

    def __str__(self) -> str:
        return self.title