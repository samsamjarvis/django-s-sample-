from django.contrib import admin
from .models import AuditLog, AdminNotification


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "user", "model_name", "object_id", "ip")
    list_filter = ("action", "model_name")
    search_fields = ("object_id", "user__email")
    readonly_fields = ("created_at", "user", "action", "model_name", "object_id", "changes", "ip", "user_agent")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(AdminNotification)
class AdminNotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "is_read", "created_at")
    list_filter = ("is_read",)
    search_fields = ("title", "message")
