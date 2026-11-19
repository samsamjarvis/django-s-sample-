from django.contrib import admin
from .models import SEOMeta, Redirect


@admin.register(SEOMeta)
class SEOMetaAdmin(admin.ModelAdmin):
    list_display = ("url_path", "title", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("url_path", "title", "description")
    readonly_fields = ("updated_at",)


@admin.register(Redirect)
class RedirectAdmin(admin.ModelAdmin):
    list_display = ("from_path", "to_path", "status_code", "is_active", "hits")
    list_filter = ("status_code", "is_active")
    search_fields = ("from_path", "to_path")
    readonly_fields = ("hits", "created_at")
