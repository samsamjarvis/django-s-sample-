from django.contrib import admin
from .models import SMSTemplate, SMSLog, OTPRequest


@admin.register(SMSTemplate)
class SMSTemplateAdmin(admin.ModelAdmin):
    list_display = ("key", "title", "is_active", "created_at")
    list_filter = ("is_active",)


@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    list_display = ("id", "template_key", "status", "provider_message_id", "created_at")
    list_filter = ("status",)
    search_fields = ("phone_hash", "provider_message_id")
    readonly_fields = ("created_at", "response_data")


@admin.register(OTPRequest)
class OTPRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "purpose", "phone_hash", "expires_at", "used_at", "created_at")
    list_filter = ("purpose",)
    readonly_fields = ("created_at", "response_data") if False else ("created_at",)
