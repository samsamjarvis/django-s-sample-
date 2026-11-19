from django.contrib import admin
from .models import Ticket, TicketMessage, LoyaltyAccount, LoyaltyTransaction, CustomerInteraction


class TicketMessageInline(admin.TabularInline):
    model = TicketMessage
    extra = 0


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "subject", "status", "priority", "assigned_to", "created_at")
    list_filter = ("status", "priority")
    search_fields = ("user__email", "subject")
    inlines = [TicketMessageInline]


@admin.register(TicketMessage)
class TicketMessageAdmin(admin.ModelAdmin):
    list_display = ("ticket", "author", "is_internal", "created_at")
    list_filter = ("is_internal",)


@admin.register(LoyaltyAccount)
class LoyaltyAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "points", "tier", "updated_at")
    list_filter = ("tier",)
    search_fields = ("user__email",)


@admin.register(LoyaltyTransaction)
class LoyaltyTransactionAdmin(admin.ModelAdmin):
    list_display = ("account", "delta", "reason", "reference", "created_at")
    readonly_fields = ("created_at",)


@admin.register(CustomerInteraction)
class CustomerInteractionAdmin(admin.ModelAdmin):
    list_display = ("user", "kind", "summary", "created_by", "created_at")
    list_filter = ("kind",)
    search_fields = ("user__email", "summary")
