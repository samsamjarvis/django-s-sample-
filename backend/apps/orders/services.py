"""
Orders Service — سبد خرید و چرخه سفارش.
ویوها فقط این ماژول را صدا می‌زنند.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.utils import timezone

from apps.customers.models import Address
from apps.inventory import services as inventory_services
from apps.inventory.models import Reservation
from apps.orders.models import (
    Cart, CartItem, Order, OrderItem, OrderStatusHistory,
)
from apps.products.models import Product

logger = logging.getLogger("silver")


class OrderError(Exception):
    """پایه خطاهای سبد/سفارش."""


class EmptyCartError(OrderError):
    pass


class CartItemNotFoundError(OrderError):
    pass


class OrderNotCancelableError(OrderError):
    pass


# ---------------------------------------------------------------------------
# Cart lifecycle
# ---------------------------------------------------------------------------
def get_or_create_cart(request) -> Cart:
    """
    سبد کاربر لاگین‌شده یا مهمان بر اساس session_key.
    اگر کاربر لاگین کرده و سبد مهمان داشت، merge می‌کند.
    """
    user = request.user if request.user.is_authenticated else None

    if user:
        cart = Cart.objects.filter(user=user, is_active=True).first()
        if cart:
            _merge_guest_cart(request, cart)
            return cart
        # شاید سبد مهمان با همین session باشد
        guest_cart = Cart.objects.filter(
            session_key=request.session.session_key, is_active=True, user__isnull=True,
        ).first()
        if guest_cart:
            guest_cart.user = user
            guest_cart.session_key = ""
            guest_cart.save(update_fields=["user", "session_key", "updated_at"])
            return guest_cart
        return Cart.objects.create(user=user)

    # مهمان
    if not request.session.session_key:
        request.session.create()
    cart, _ = Cart.objects.get_or_create(
        session_key=request.session.session_key, user__isnull=True, is_active=True,
    )
    return cart


def _merge_guest_cart(request, user_cart: Cart) -> None:
    """ادغام سبد مهمان هنگام ورود — بر اساس product."""
    sk = request.session.session_key
    if not sk:
        return
    guest = Cart.objects.filter(session_key=sk, user__isnull=True, is_active=True).first()
    if not guest or guest.id == user_cart.id:
        return
    for item in guest.items.select_related("product", "reservation"):
        existing = user_cart.items.filter(product=item.product).first()
        if existing:
            _combine_quantities(existing, item)
        else:
            item.cart = user_cart
            item.save(update_fields=["cart", "updated_at"])
    guest.is_active = False
    guest.save(update_fields=["is_active", "updated_at"])
    logger.info("cart_merge user=%s guest=%s", user_cart.user_id, guest.id)


def _combine_quantities(existing: CartItem, incoming: CartItem) -> None:
    """ادغام امن دو CartItem — یا رزرو جدید یا آزادسازی."""
    extra = incoming.quantity
    try:
        new_res = inventory_services.reserve_stock(
            existing.product, extra, user=existing.cart.user,
            reference=f"cart-{existing.cart_id}",
        )
        existing.quantity += extra
        existing.save(update_fields=["quantity", "updated_at"])
        existing.reservation = new_res
        existing.save(update_fields=["reservation"])
    except inventory_services.InventoryError:
        pass  # موجودی کافی نبود، سرجایش می‌ماند
    if incoming.reservation_id:
        inventory_services.release_reservation(incoming.reservation, reason="merged")
    incoming.delete()


@transaction.atomic
def add_to_cart(
    cart: Cart, product: Product, quantity: int = 1,
) -> CartItem:
    """
    افزودن به سبد + رزرو موجودی. در صورت وجود آیتم قبلی، ادغام می‌کند.
    """
    if quantity <= 0:
        raise OrderError("تعداد باید بزرگ‌تر از صفر باشد.")

    existing = CartItem.objects.select_for_update().filter(
        cart=cart, product=product,
    ).first()
    if existing:
        new_qty = existing.quantity + quantity
        # رزرو بیشتر برای اختلاف
        reservation = inventory_services.reserve_stock(
            product, quantity, user=cart.user, reference=f"cart-{cart.id}",
        )
        existing.quantity = new_qty
        existing.reservation = reservation
        existing.unit_price = product.final_price
        existing.save(update_fields=["quantity", "reservation", "unit_price", "updated_at"])
        logger.info("cart_add_merged cart=%s product=%s qty=%s", cart.id, product.id, new_qty)
        return existing

    reservation = inventory_services.reserve_stock(
        product, quantity, user=cart.user, reference=f"cart-{cart.id}",
    )
    item = CartItem.objects.create(
        cart=cart, product=product, quantity=quantity,
        unit_price=product.final_price, reservation=reservation,
    )
    logger.info("cart_add cart=%s product=%s qty=%s res=%s",
                cart.id, product.id, quantity, reservation.id)
    return item


@transaction.atomic
def update_cart_item(item: CartItem, new_quantity: int) -> CartItem:
    """تغییر تعداد — تفاضل رزرو می‌شود."""
    if new_quantity < 1:
        raise OrderError("تعداد باید حداقل ۱ باشد.")
    delta = new_quantity - item.quantity
    if delta == 0:
        return item

    if delta > 0:
        new_res = inventory_services.reserve_stock(
            item.product, delta, user=item.cart.user,
            reference=f"cart-{item.cart_id}",
        )
        if item.reservation_id:
            # ادغام: رزرو قبلی را نگه دار، فقط رزرو جدید را آزاد کن
            inventory_services.release_reservation(new_res, reason="merge_into_existing")
        else:
            item.reservation = new_res
    else:
        # کاهش: بخشی از رزرو را آزاد کن (رزرو اصلی دست‌نخورده، ولی reserved را کم می‌کنیم)
        from apps.inventory.models import Reservation as Res
        from datetime import timedelta
        # آزادسازی جزئی: رزرو جدید با مقدار کم می‌سازیم و رزرو قبلی را آزاد
        old_qty = abs(delta)
        if item.reservation:
            res = item.reservation
            # کاهش reserved و سپس اگر رزرو قبلی باید تقسیم شود:
            from apps.inventory.models import Stock
            from django.db.models import F
            stock = Stock.objects.select_for_update().get(product=item.product)
            stock.reserved_quantity = F("reserved_quantity") - old_qty
            stock.save(update_fields=["reserved_quantity", "updated_at"])
            res.quantity -= old_qty
            res.save(update_fields=["quantity", "updated_at"])

    item.quantity = new_quantity
    item.unit_price = item.product.final_price
    item.save(update_fields=["quantity", "unit_price", "updated_at"])
    logger.info("cart_update item=%s qty=%s", item.id, new_quantity)
    return item


@transaction.atomic
def remove_from_cart(item: CartItem) -> None:
    if item.reservation_id:
        inventory_services.release_reservation(item.reservation, reason="removed")
    logger.info("cart_remove item=%s product=%s", item.id, item.product_id)
    item.delete()


@transaction.atomic
def clear_cart(cart: Cart) -> None:
    for item in cart.items.select_related("reservation"):
        if item.reservation_id:
            inventory_services.release_reservation(item.reservation, reason="cleared")
    cart.items.all().delete()
    logger.info("cart_clear cart=%s", cart.id)


# ---------------------------------------------------------------------------
# Order lifecycle
# ---------------------------------------------------------------------------
@transaction.atomic
def finalize_order(
    cart: Cart, *, shipping_address: Address,
    user,
    customer_note: str = "",
    discount_amount: Decimal = Decimal("0"),
    shipping_amount: Decimal = Decimal("0"),
) -> Order:
    """
    تبدیل سبد به سفارش. پیش‌نیاز پرداخت.
    - snapshot آدرس
    - snapshot محصول
    - رزروها همچنان قفل هستند تا پرداخت موفق
    """
    items = list(cart.items.select_related("product", "reservation"))
    if not items:
        raise EmptyCartError("سبد خرید خالی است.")

    subtotal = sum((Decimal(i.unit_price) * i.quantity for i in items), Decimal("0"))
    total = subtotal - discount_amount + shipping_amount
    if total < 0:
        total = Decimal("0")

    order = Order.objects.create(
        user=user,
        subtotal_amount=subtotal,
        discount_amount=discount_amount,
        shipping_amount=shipping_amount,
        total_amount=total,
        shipping_full_name=shipping_address.recipient_name,
        shipping_phone=shipping_address.recipient_phone,
        shipping_province=shipping_address.province,
        shipping_city=shipping_address.city,
        shipping_address=shipping_address.full_address or "",
        shipping_postal_code=shipping_address.postal_code or "",
        customer_note=customer_note,
    )

    for i in items:
        OrderItem.objects.create(
            order=order,
            product=i.product,
            product_name=i.product.name,
            product_image_path=i.product.main_image.image.name if i.product.main_image else "",
            unit_price=i.unit_price,
            quantity=i.quantity,
        )

    OrderStatusHistory.objects.create(
        order=order, from_status="", to_status=order.status,
        note="سفارش ایجاد شد", changed_by=user,
    )

    logger.info("order_finalize order=%s total=%s items=%s",
                order.order_number, total, len(items))
    return order


@transaction.atomic
def mark_paid(order: Order, *, payment_id: Optional[int] = None) -> Order:
    """
    پرداخت موفق → وضعیت paid، مصرف رزروها، ثبت تاریخ.
    این تابع توسط PaymentService صدا زده می‌شود.
    """
    if order.payment_status == Order.PAYMENT_PAID:
        return order

    # ۱) مصرف تمام رزروهای مربوط به این سفارش
    for item in order.items.select_related("product"):
        # رزروها بر اساس order_reference ممکن است چند باشند
        reservations = Reservation.objects.filter(
            status=Reservation.STATUS_ACTIVE,
            user=order.user,
            product=item.product,
            order_reference__startswith=f"order-{order.order_number}",
        )
        # اگر پیدا نشد، تلاش با cart- prefixed
        if not reservations.exists():
            reservations = Reservation.objects.filter(
                status=Reservation.STATUS_ACTIVE,
                user=order.user,
                product=item.product,
            )[:1]
        for res in reservations:
            inventory_services.consume_reservation(res, reference=f"order-{order.order_number}")

    order.payment_status = Order.PAYMENT_PAID
    order.status = Order.STATUS_PAID
    order.paid_at = timezone.now()
    order.save(update_fields=["payment_status", "status", "paid_at", "updated_at"])
    OrderStatusHistory.objects.create(
        order=order, from_status=Order.STATUS_PENDING, to_status=Order.STATUS_PAID,
        note=f"پرداخت موفق (payment_id={payment_id})",
    )
    logger.info("order_paid order=%s payment=%s", order.order_number, payment_id)

    # ارسال پیامک و اعلان بعد از commit
    from apps.orders import signals as order_signals
    order_signals.on_order_paid.send(sender=Order, order=order)

    return order


@transaction.atomic
def mark_payment_failed(order: Order, reason: str = "") -> Order:
    if order.payment_status == Order.PAYMENT_PAID:
        return order
    order.payment_status = Order.PAYMENT_FAILED
    order.save(update_fields=["payment_status", "updated_at"])
    logger.warning("order_payment_failed order=%s reason=%s", order.order_number, reason)
    return order


@transaction.atomic
def cancel_order(order: Order, *, user=None, reason: str = "") -> Order:
    if not order.is_cancelable:
        raise OrderNotCancelableError("این سفارش قابل لغو نیست.")

    # آزادسازی رزروهای باقی‌مانده
    reservations = Reservation.objects.filter(
        status=Reservation.STATUS_ACTIVE,
        order_reference__icontains=order.order_number,
    )
    for res in reservations:
        inventory_services.release_reservation(res, reason="order_canceled")

    # بازگشت موجودی اگر پرداخت شده بود
    if order.payment_status == Order.PAYMENT_PAID:
        for item in order.items.select_related("product"):
            try:
                inventory_services.adjust_stock(
                    item.product, item.quantity,
                    reason=f"cancel {order.order_number}", user=user,
                )
            except inventory_services.InventoryError as exc:
                logger.warning("cancel_stock_restore_failed order=%s err=%s",
                               order.order_number, exc)

    prev = order.status
    order.status = Order.STATUS_CANCELED
    order.canceled_at = timezone.now()
    order.save(update_fields=["status", "canceled_at", "updated_at"])
    OrderStatusHistory.objects.create(
        order=order, from_status=prev, to_status=Order.STATUS_CANCELED,
        note=reason or "لغو سفارش", changed_by=user,
    )
    logger.info("order_canceled order=%s reason=%s", order.order_number, reason)
    return order


@transaction.atomic
def transition_status(
    order: Order, to_status: str, *, note: str = "", user=None,
) -> Order:
    """جابه‌جایی بین وضعیت‌های میانی (processing/shipped/delivered)."""
    valid = {
        Order.STATUS_PAID: [Order.STATUS_PROCESSING],
        Order.STATUS_PROCESSING: [Order.STATUS_SHIPPED],
        Order.STATUS_SHIPPED: [Order.STATUS_DELIVERED],
    }
    if to_status not in valid.get(order.status, []):
        raise OrderError(f"گذار از {order.status} به {to_status} مجاز نیست.")

    prev = order.status
    order.status = to_status
    if to_status == Order.STATUS_SHIPPED:
        order.shipped_at = timezone.now()
    if to_status == Order.STATUS_DELIVERED:
        order.delivered_at = timezone.now()
    order.save(update_fields=["status", "shipped_at", "delivered_at", "updated_at"])
    OrderStatusHistory.objects.create(
        order=order, from_status=prev, to_status=to_status,
        note=note, changed_by=user,
    )
    logger.info("order_status order=%s %s→%s", order.order_number, prev, to_status)
    return order


def user_orders(user) -> "QuerySet[Order]":
    return Order.objects.filter(user=user).prefetch_related("items").order_by("-created_at")