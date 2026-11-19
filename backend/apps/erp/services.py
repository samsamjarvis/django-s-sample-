"""
ERP Service — تأمین‌کننده، سفارش خرید، هزینه.
"""
from __future__ import annotations

import logging
import uuid
from decimal import Decimal
from typing import Iterable, Optional

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.erp.models import (
    Expense, PurchaseOrder, PurchaseOrderItem, Supplier,
)
from apps.inventory import services as inventory_services
from apps.products.models import Product

logger = logging.getLogger("silver.erp")


class ERPError(Exception):
    pass


def _new_po_reference() -> str:
    return "PO-" + uuid.uuid4().hex[:10].upper()


@transaction.atomic
def create_purchase_order(
    supplier: Supplier, items: Iterable[dict], *,
    expected_at=None, notes: str = "", user=None,
) -> PurchaseOrder:
    """
    items: [{"product": Product, "quantity": int, "unit_cost": Decimal}, ...]
    """
    items = list(items)
    if not items:
        raise ERPError("سفارش خرید باید حداقل یک آیتم داشته باشد.")

    po = PurchaseOrder.objects.create(
        supplier=supplier,
        reference=_new_po_reference(),
        expected_at=expected_at,
        notes=notes,
        created_by=user,
        status=PurchaseOrder.STATUS_ORDERED,
    )
    total = Decimal("0")
    for it in items:
        qty = int(it["quantity"])
        cost = Decimal(it["unit_cost"])
        PurchaseOrderItem.objects.create(
            purchase_order=po, product=it["product"],
            quantity=qty, unit_cost=cost,
        )
        total += cost * qty
    po.total_cost = total
    po.save(update_fields=["total_cost", "updated_at"])
    logger.info("po_create ref=%s supplier=%s total=%s",
                po.reference, supplier.id, total)
    return po


@transaction.atomic
def receive_purchase_order(po: PurchaseOrder, *, user=None) -> PurchaseOrder:
    """دریافت سفارش خرید → افزایش موجودی هر آیتم."""
    if po.status == PurchaseOrder.STATUS_RECEIVED:
        return po
    if po.status == PurchaseOrder.STATUS_CANCELED:
        raise ERPError("سفارش خرید لغو شده است.")

    for item in po.items.select_related("product"):
        inventory_services.adjust_stock(
            item.product, item.quantity,
            reason=f"PO {po.reference}", user=user,
        )
    po.status = PurchaseOrder.STATUS_RECEIVED
    po.save(update_fields=["status", "updated_at"])
    logger.info("po_receive ref=%s", po.reference)
    return po


@transaction.atomic
def cancel_purchase_order(po: PurchaseOrder, *, by=None) -> PurchaseOrder:
    if po.status == PurchaseOrder.STATUS_RECEIVED:
        raise ERPError("سفارش دریافت‌شده قابل لغو نیست.")
    po.status = PurchaseOrder.STATUS_CANCELED
    po.save(update_fields=["status", "updated_at"])
    logger.info("po_cancel ref=%s", po.reference)
    return po


@transaction.atomic
def record_expense(
    *, category: str, amount: Decimal, description: str,
    paid_at=None, user=None,
) -> Expense:
    if amount <= 0:
        raise ERPError("مبلغ هزینه باید مثبت باشد.")
    exp = Expense.objects.create(
        category=category, amount=amount, description=description,
        paid_at=paid_at or timezone.now().date(), created_by=user,
    )
    logger.info("expense_create id=%s amount=%s", exp.id, amount)
    return exp


# ---------------------------------------------------------------------------
# Reporting helpers
# ---------------------------------------------------------------------------
def expense_summary(start_date, end_date):
    return (
        Expense.objects.filter(paid_at__range=(start_date, end_date))
        .values("category")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )


def purchase_summary(start_date, end_date):
    return (
        PurchaseOrder.objects.filter(
            created_at__date__range=(start_date, end_date),
            status=PurchaseOrder.STATUS_RECEIVED,
        )
        .values("supplier__name")
        .annotate(total=Sum("total_cost"))
        .order_by("-total")
    )