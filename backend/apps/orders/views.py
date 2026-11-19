"""Orders views — سبد خرید و سفارش‌ها."""
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from apps.customers.models import Address
from apps.inventory.services import InventoryError
from apps.orders import services as order_services
from apps.orders.models import CartItem, Order
from apps.products.models import Product
from .forms import CartAddForm, CheckoutForm

logger = logging.getLogger("silver.orders")


def _wants_json(request):
    return (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in request.headers.get("Accept", "")
    )


# ══════════════════════════════════════════════════════════════════
# Cart
# ══════════════════════════════════════════════════════════════════

def cart_view(request):
    cart = order_services.get_or_create_cart(request)
    items = (
        cart.items
        .select_related("product", "product__category")
        .prefetch_related("product__images")
    )
    return render(request, "orders/cart.html", {"cart": cart, "items": items})


@require_POST
def cart_add(request):
    form = CartAddForm(request.POST)
    if not form.is_valid():
        if _wants_json(request):
            return JsonResponse({"ok": False, "error": "invalid"}, status=400)
        messages.error(request, "درخواست نامعتبر.")
        return redirect("cart:view")

    product = get_object_or_404(
        Product, id=form.cleaned_data["product_id"], is_active=True,
    )
    cart = order_services.get_or_create_cart(request)

    try:
        order_services.add_to_cart(cart, product, form.cleaned_data["quantity"])
    except (order_services.OrderError, InventoryError) as exc:
        if _wants_json(request):
            return JsonResponse({"ok": False, "error": str(exc)}, status=400)
        messages.error(request, str(exc))
        return redirect("cart:view")
    except Exception:
        logger.exception("cart_add_failed product=%s", product.id)
        if _wants_json(request):
            return JsonResponse({"ok": False, "error": "server_error"}, status=500)
        messages.error(request, "خطا در افزودن به سبد. لطفاً بعداً تلاش کنید.")
        return redirect("cart:view")

    if _wants_json(request):
        return JsonResponse({"ok": True, "total_qty": cart.total_quantity})
    messages.success(request, "به سبد اضافه شد.")
    return redirect("cart:view")


@require_POST
def cart_update(request, item_id):
    item = get_object_or_404(CartItem, id=item_id)
    cart = order_services.get_or_create_cart(request)
    if item.cart_id != cart.id:
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)
    try:
        qty = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        qty = 1
    try:
        order_services.update_cart_item(item, qty)
    except (order_services.OrderError, InventoryError) as exc:
        messages.error(request, str(exc))
    except Exception:
        logger.exception("cart_update_failed item=%s", item_id)
        messages.error(request, "خطا در به‌روزرسانی.")
    return redirect("cart:view")


@require_POST
def cart_remove(request, item_id):
    item = get_object_or_404(CartItem, id=item_id)
    cart = order_services.get_or_create_cart(request)
    if item.cart_id == cart.id:
        order_services.remove_from_cart(item)
        messages.success(request, "آیتم حذف شد.")
    return redirect("cart:view")


@require_POST
def cart_clear(request):
    cart = order_services.get_or_create_cart(request)
    order_services.clear_cart(cart)
    messages.success(request, "سبد خرید خالی شد.")
    return redirect("cart:view")


# ══════════════════════════════════════════════════════════════════
# Checkout & Orders
# ══════════════════════════════════════════════════════════════════

@login_required
@require_http_methods(["GET", "POST"])
def checkout(request):
    cart = order_services.get_or_create_cart(request)
    if not cart.items.exists():
        messages.warning(request, "سبد خرید خالی است.")
        return redirect("cart:view")

    if not Address.objects.filter(user=request.user).exists():
        messages.info(request, "ابتدا یک آدرس تحویل اضافه کنید.")
        return redirect("customers:address_add")

    form = CheckoutForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            order = order_services.finalize_order(
                cart,
                shipping_address=form.cleaned_data["address"],
                user=request.user,
                customer_note=form.cleaned_data.get("customer_note", ""),
            )
        except order_services.EmptyCartError:
            messages.error(request, "سبد خالی است.")
            return redirect("cart:view")
        except Exception:
            logger.exception("checkout_finalize_failed user=%s", request.user.id)
            messages.error(request, "خطا در ثبت سفارش.")
            return redirect("cart:view")
        return redirect("payment:initiate", order_id=order.id)

    return render(request, "orders/checkout.html", {"form": form, "cart": cart})


@login_required
def order_list(request):
    return render(request, "orders/list.html", {
        "orders": order_services.user_orders(request.user),
    })


@login_required
def order_detail(request, order_number):
    order = get_object_or_404(
        Order.objects.prefetch_related("items", "status_history", "payments"),
        order_number=order_number, user=request.user,
    )
    return render(request, "orders/detail.html", {"order": order})


@login_required
@require_POST
def order_cancel(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    try:
        order_services.cancel_order(order, user=request.user, reason="درخواست کاربر")
        messages.success(request, "سفارش لغو شد.")
    except order_services.OrderNotCancelableError as exc:
        messages.error(request, str(exc))
    except Exception:
        logger.exception("order_cancel_failed order=%s", order_number)
        messages.error(request, "خطا در لغو سفارش.")
    return redirect("orders:detail", order_number=order_number)
