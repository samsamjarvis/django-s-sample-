"""
دستور آزادسازی رزروهای منقضی. در cron هر ۵ دقیقه اجرا شود.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.inventory import services as inventory_services


class Command(BaseCommand):
    help = "آزادسازی رزروهای منقضی‌شده (سبدهای رهاشده)."

    def handle(self, *args, **options):
        started = timezone.now()
        count = inventory_services.expire_stale_reservations()
        elapsed = (timezone.now() - started).total_seconds()
        self.stdout.write(
            self.style.SUCCESS(
                f"{count} reservation(s) released in {elapsed:.2f}s"
            )
        )