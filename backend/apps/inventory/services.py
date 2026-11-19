"""
Inventory Service — تمام تغییرات موجودی، رزرو، و آزادسازی.
هر ویو باید از این سرویس استفاده کند؛ هرگز مستقیم Stock را آپدیت نکن.
"""
from __future__ import annotations

import logging
from typing import Optional

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.inventory.models import Reservation, Stock, StockMovement
from apps.products.models import Product

logger = logging.getLogger("silver")


class InventoryError(Exception):
    """پایه خطاهای انبار — ویوها این را می‌گیرند."""


class InsufficientStockError(InventoryError):
    def __init__(self, product: Product, requested: int, available: int):
        self.product = product
        self.requested = requested
        self.available = available
        super().__init__(f"موجودی «{product.name}» کافی نیست (درخواست: {requested}، موجود: {available}).")


class ProductInactiveError(InventoryError):
    def __init__(self, product: Product):
        self.product = product
        super().__init__(f"محصول «{product.name}» غیرفعال است.")


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------
def get_available(product: Product) -> int:
    """موجودی قابل فروش = quantity - reserved."""
    try:
        stock = product.stock
    except Stock.DoesNotExist:
        return 0
    return max(stock.quantity - stock.reserved_quantity, 0)


def is_low_stock(product: Product) -> bool:
    try:
        return product.stock.is_low
    except Stock.DoesNotExist:
        return True


# ---------------------------------------------------------------------------
# Movements (audit log)
# ---------------------------------------------------------------------------
def _record_movement(
    product: Product, kind: str, quantity: int, *,
    reason: str = "", reference: str = "", user=None,
) -> StockMovement:
    return StockMovement.objects.create(
        product=product, kind=kind, quantity=quantity,
        reason=reason, reference=reference, created_by=user,
    )


# ---------------------------------------------------------------------------
# Stock adjustments (admin only)
# ---------------------------------------------------------------------------
@transaction.atomic
def adjust_stock(
    product: Product, delta: int, *, reason: str = "",
    user=None, allow_negative: bool = False,
) -> Stock:
    """
    تغییر مستقیم موجودی (فقط ادمین). delta مثبت=ورود، منفی=خروج.
    """
    stock, _ = Stock.objects.select_for_update().get_or_create(product=product)
    new_qty = stock.quantity + delta
    if new_qty < 0 and not allow_negative:
        raise InsufficientStockError(product, abs(delta), stock.quantity)
    stock.quantity = max(new_qty, 0) if not allow_negative else new_qty
    stock.save(update_fields=["quantity", "updated_at"])
    _record_movement(
        product, StockMovement.TYPE_IN if delta > 0 else StockMovement.TYPE_OUT,
        delta, reason=reason, user=user,
    )
    logger.info("stock_adjust product=%s delta=%s new=%s by=%s",
                product.id, delta, stock.quantity, getattr(user, "id", None))
    return stock


@transaction.atomic
def set_stock_quantity(product: Product, new_quantity: int, *, reason: str = "", user=None) -> Stock:
    """تنظیم مطلق — فقط ادمین."""
    if new_quantity < 0:
        raise InventoryError("موجودی نمی‌تواند منفی باشد.")
    stock, _ = Stock.objects.select_for_update().get_or_create(product=product)
    delta = new_quantity - stock.quantity
    stock.quantity = new_quantity
    stock.save(update_fields=["quantity", "updated_at"])
    _record_movement(product, StockMovement.TYPE_ADJUST, delta, reason=reason, user=user)
    return stock


# ---------------------------------------------------------------------------
# Reservations (سبد خرید)
# ---------------------------------------------------------------------------
@transaction.atomic
def reserve_stock(
    product: Product, quantity: int, *,
    user=None, reference: str = "", ttl_minutes: Optional[int] = None,
) -> Reservation:
    """
    رزرو موجودی برای سبد. اگر موجودی کافی نباشد InsufficientStockError.
    TTL پیش‌فرض ۳۰ دقیقه. آزادسازی خودکار با مدیریت command در فاز ۹.
    """
    if not product.is_active:
        raise ProductInactiveError(product)
    if quantity <= 0:
        raise InventoryError("تعداد باید بزرگ‌تر از صفر باشد.")

    stock, _ = Stock.objects.select_for_update().get_or_create(product=product)
    available = max(stock.quantity - stock.reserved_quantity, 0)
    if available < quantity:
        raise InsufficientStockError(product, quantity, available)

    stock.reserved_quantity = F("reserved_quantity") + quantity
    stock.save(update_fields=["reserved_quantity", "updated_at"])
    stock.refresh_from_db(fields=["reserved_quantity"])

    expires_at = Reservation.default_expiry()
    if ttl_minutes is not None:
        from datetime import timedelta
        expires_at = timezone.now() + timedelta(minutes=ttl_minutes)

    reservation = Reservation.objects.create(
        user=user, product=product, quantity=quantity,
        status=Reservation.STATUS_ACTIVE, expires_at=expires_at, order_reference=reference,
    )
    _record_movement(
        product, StockMovement.TYPE_RESERVE, quantity,
        reason="reserve", reference=f"res-{reservation.id}",
    )
    logger.info("reserve product=%s qty=%s res=%s exp=%s",
                product.id, quantity, reservation.id, expires_at.isoformat())
    return reservation


@transaction.atomic
def release_reservation(reservation: Reservation, *, reason: str = "released") -> Reservation:
    """
    آزادسازی رزرو (لغو سبد / انقضا / خطا). idempotent.
    """
    if reservation.status != Reservation.STATUS_ACTIVE:
        return reservation

    stock, _ = Stock.objects.select_for_update().get_or_create(product=reservation.product)
    stock.reserved_quantity = max(stock.reserved_quantity - reservation.quantity, 0)
    stock.save(update_fields=["reserved_quantity", "updated_at"])

    reservation.status = (
        Reservation.STATUS_EXPIRED if reason == "expired" else Reservation.STATUS_RELEASED
    )
    reservation.save(update_fields=["status", "updated_at"])
    _record_movement(
        reservation.product, StockMovement.TYPE_RELEASE, -reservation.quantity,
        reason=reason, reference=f"res-{reservation.id}",
    )
    logger.info("release res=%s reason=%s", reservation.id, reason)
    return reservation


@transaction.atomic
def consume_reservation(reservation: Reservation, *, reference: str = "") -> Reservation:
    """
    تبدیل رزرو به فروش (پس از پرداخت موفق). quantity کم می‌شود و رزرو مصرف می‌شود.
    """
    if reservation.status != Reservation.STATUS_ACTIVE:
        return reservation

    stock, _ = Stock.objects.select_for_update().get_or_create(product=reservation.product)
    qty = reservation.quantity
    if stock.quantity < qty:
        # این وضعیت نباید اتفاق بیفتد چون رزرو موجودی را قفل کرده، ولی برای اطمینان:
        raise InsufficientStockError(reservation.product, qty, stock.quantity)

    stock.quantity = F("quantity") - qty
    stock.reserved_quantity = F("reserved_quantity") - qty
    stock.save(update_fields=["quantity", "reserved_quantity", "updated_at"])
    stock.refresh_from_db(fields=["quantity", "reserved_quantity"])

    reservation.status = Reservation.STATUS_CONSUMED
    reservation.order_reference = reference or reservation.order_reference
    reservation.save(update_fields=["status", "order_reference", "updated_at"])

    _record_movement(
        reservation.product, StockMovement.TYPE_OUT, -qty,
        reason="sold", reference=reference or f"res-{reservation.id}",
    )
    logger.info("consume res=%s product=%s qty=%s", reservation.id, reservation.product_id, qty)
    return reservation


@transaction.atomic
def expire_stale_reservations() -> int:
    """
    آزادسازی رزروهای منقضی‌شده. از management command صدا زده می‌شود.
    برمی‌گرداند تعداد رزروهای آزادشده.
    """
    now = timezone.now()
    qs = Reservation.objects.select_for_update().filter(
        status=Reservation.STATUS_ACTIVE, expires_at__lt=now,
    )
    count = 0
    for res in qs:
        release_reservation(res, reason="expired")
        count += 1
    if count:
        logger.info("expire_stale_reservations count=%s", count)
    return count