"""Dashboard views — پنل ادمین اختصاصی."""
import logging
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from apps.accounts.models import User
from apps.crm.models import LoyaltyAccount, Ticket
from apps.customers.models import Address
from apps.dashboard import services as dash_services
from apps.dashboard.decorators import staff_required
from apps.dashboard.models import AuditLog
from apps.erp import services as erp_services
from apps.inventory import services as inventory_services
from apps.inventory.models import Stock
from apps.orders import services as order_services
from apps.orders.models import Order
from apps.payment.models import Payment
from apps.products.models import Category, Product, ProductImage
from apps.sms.models import SMSLog
from .forms import (
    CategoryAdminForm, GatewaySettingsForm, ProductAdminForm,
    SiteSettingsPanelForm, StockAdjustForm,
)

logger = logging.getLogger("silver.dashboard")


def admin_login_redirect(request):
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        return redirect("dashboard:home")
    return redirect(f"{reverse('accounts:login')}?next={reverse('dashboard:home')}")


@staff_required
def admin_home(request):
    from django.core.cache import cache
    cache_key = "admin_home_kpi_v1"
    kpi = cache.get(cache_key)
    if kpi is None:
        now = timezone.now()
        today = now.date()
        last_7d = now - timedelta(days=7)
        kpi = {
            "orders_today": Order.objects.filter(created_at__date=today).count(),
            "revenue_today": Order.objects.filter(
                created_at__date=today, payment_status=Order.PAYMENT_PAID,
            ).aggregate(t=Sum("total_amount"))["t"] or 0,
            "orders_7d": Order.objects.filter(created_at__gte=last_7d).count(),
            "revenue_7d": Order.objects.filter(
                created_at__gte=last_7d, payment_status=Order.PAYMENT_PAID,
            ).aggregate(t=Sum("total_amount"))["t"] or 0,
            "total_customers": User.objects.filter(is_active=True, is_customer=True).count(),
            "open_tickets": Ticket.objects.filter(status=Ticket.STATUS_OPEN).count(),
        }
        cache.set(cache_key, kpi, 120)

    return render(request, "dashboard/admin_home.html", {
        **kpi,
        "recent_orders": Order.objects.select_related("user").order_by("-created_at")[:10],
        "low_stock": Stock.objects.filter(quantity__lte=3, quantity__gt=0).select_related("product")[:10],
        "unread_notifications": request.user.admin_notifications.filter(is_read=False).count(),
    })


# ═════════ Products ═════════
@staff_required
def product_list(request):
    qs = Product.objects.select_related("category").prefetch_related("images").order_by("-created_at")
    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(name__icontains=q)
    page = Paginator(qs, 20).get_page(request.GET.get("page"))
    return render(request, "dashboard/admin_products.html", {"page": page, "q": q})


@staff_required
@require_http_methods(["GET", "POST"])
def product_form(request, pk=None):
    product = get_object_or_404(Product, pk=pk) if pk else None
    form = ProductAdminForm(request.POST or None, request.FILES or None, instance=product)

    if request.method == "POST" and form.is_valid():
        obj = form.save()

        new_images = request.FILES.getlist("new_images")
        has_main = obj.images.filter(is_main=True).exists()

        for idx, img_file in enumerate(new_images):
            try:
                ProductImage.objects.create(
                    product=obj,
                    image=img_file,
                    alt_text=obj.name,
                    is_main=(not has_main and idx == 0),
                    sort_order=idx,
                )
                if not has_main and idx == 0:
                    has_main = True
            except Exception:
                logger.exception("product_image_upload_failed product=%s", obj.id)

        try:
            dash_services.log_action(
                user=request.user,
                action="product_update" if pk else "product_create",
                model_name="Product", object_id=obj.id, request=request,
            )
        except Exception:
            pass

        messages.success(request, "محصول ذخیره شد.")
        return redirect("dashboard:product_edit", pk=obj.pk)

    return render(request, "dashboard/admin_product_form.html", {
        "form": form,
        "product": product,
        "images": product.images.all() if product else [],
    })


@staff_required
@require_POST
def product_image_delete(request, pk, img_id):
    product = get_object_or_404(Product, pk=pk)
    image = get_object_or_404(ProductImage, pk=img_id, product=product)
    was_main = image.is_main
    try:
        image.image.delete(save=False)
    except Exception:
        pass
    image.delete()

    if was_main:
        next_img = product.images.first()
        if next_img:
            next_img.is_main = True
            next_img.save(update_fields=["is_main"])

    messages.success(request, "تصویر حذف شد.")
    return redirect("dashboard:product_edit", pk=product.pk)


@staff_required
@require_POST
def product_image_set_main(request, pk, img_id):
    product = get_object_or_404(Product, pk=pk)
    image = get_object_or_404(ProductImage, pk=img_id, product=product)
    ProductImage.objects.filter(product=product, is_main=True).update(is_main=False)
    image.is_main = True
    image.save(update_fields=["is_main"])
    messages.success(request, "تصویر اصلی تنظیم شد.")
    return redirect("dashboard:product_edit", pk=product.pk)


# ═════════ Orders ═════════
@staff_required
def order_list(request):
    qs = Order.objects.select_related("user").order_by("-created_at")
    status = request.GET.get("status")
    if status:
        qs = qs.filter(status=status)
    page = Paginator(qs, 20).get_page(request.GET.get("page"))
    return render(request, "dashboard/admin_orders.html", {
        "page": page, "status": status, "status_choices": Order.STATUS_CHOICES,
    })


@staff_required
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.select_related("user").prefetch_related("items", "status_history", "payments"),
        pk=pk,
    )
    return render(request, "dashboard/admin_order_detail.html", {"order": order})


@staff_required
@require_POST
def order_action(request, pk, action):
    order = get_object_or_404(Order, pk=pk)
    try:
        if action == "processing":
            order_services.transition_status(order, Order.STATUS_PROCESSING, user=request.user)
        elif action == "shipped":
            order_services.transition_status(order, Order.STATUS_SHIPPED, user=request.user)
        elif action == "delivered":
            order_services.transition_status(order, Order.STATUS_DELIVERED, user=request.user)
        elif action == "cancel":
            order_services.cancel_order(order, user=request.user, reason="لغو توسط ادمین")
        else:
            messages.error(request, "عملیات نامعتبر.")
            return redirect("dashboard:order_detail", pk=pk)
    except order_services.OrderError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "وضعیت به‌روز شد.")
        try:
            dash_services.log_action(
                user=request.user, action=f"order_{action}",
                model_name="Order", object_id=order.id, request=request,
            )
        except Exception:
            pass
    return redirect("dashboard:order_detail", pk=pk)


# ═════════ Customers ═════════
@staff_required
def customer_list(request):
    qs = User.objects.filter(is_customer=True).annotate(order_count=Count("orders")).order_by("-date_joined")
    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(email__icontains=q)
    page = Paginator(qs, 20).get_page(request.GET.get("page"))
    return render(request, "dashboard/admin_customers.html", {"page": page, "q": q})


@staff_required
def customer_detail(request, pk):
    customer = get_object_or_404(User, pk=pk, is_customer=True)
    return render(request, "dashboard/admin_customer_detail.html", {
        "customer": customer,
        "orders": Order.objects.filter(user=customer).order_by("-created_at")[:20],
        "loyalty": LoyaltyAccount.objects.filter(user=customer).first(),
        "addresses": Address.objects.filter(user=customer),
    })


# ═════════ Inventory ═════════
@staff_required
def inventory_list(request):
    qs = Stock.objects.select_related("product").order_by("quantity")
    page = Paginator(qs, 30).get_page(request.GET.get("page"))
    return render(request, "dashboard/admin_inventory.html", {"page": page})


@staff_required
@require_http_methods(["GET", "POST"])
def stock_adjust(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    form = StockAdjustForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            inventory_services.adjust_stock(
                product, form.cleaned_data["delta"],
                reason=form.cleaned_data.get("reason", ""), user=request.user,
            )
        except inventory_services.InventoryError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, "موجودی به‌روز شد.")
            return redirect("dashboard:inventory_list")
    return render(request, "dashboard/admin_inventory_adjust.html", {"form": form, "product": product})


# ═════════ Payments ═════════
@staff_required
def payment_list(request):
    qs = Payment.objects.select_related("order", "order__user").order_by("-created_at")
    status = request.GET.get("status")
    if status:
        qs = qs.filter(status=status)
    page = Paginator(qs, 40).get_page(request.GET.get("page"))
    return render(request, "dashboard/admin_payments.html", {
        "page": page, "status": status, "status_choices": Payment.STATUS_CHOICES,
    })


@staff_required
@require_http_methods(["GET", "POST"])
def payment_settings(request):
    from apps.core.models import SiteSettings
    settings_obj = SiteSettings.get_solo()
    form = GatewaySettingsForm(request.POST or None, instance=settings_obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "تنظیمات به‌روز شد.")
        return redirect("dashboard:payment_settings")
    return render(request, "dashboard/admin_payment_settings.html", {"form": form, "settings_obj": settings_obj})


@staff_required
@require_POST
def payment_reconcile(request, pk):
    from apps.payment import services as payment_services
    payment = get_object_or_404(Payment, pk=pk)
    try:
        result = payment_services.reconcile_payment(payment)
    except Exception:
        logger.exception("admin_reconcile_failed payment=%s", payment.id)
        messages.error(request, "خطا در همگام‌سازی.")
    else:
        if result == "paid":
            messages.success(request, "پرداخت تأیید شد.")
        elif result == "failed":
            messages.warning(request, "پرداخت ناموفق علامت‌گذاری شد.")
        else:
            messages.info(request, "پرداخت همچنان در انتظار است.")
    return redirect("dashboard:payment_list")


@staff_required
@require_POST
def payment_refund(request, pk):
    from apps.payment import services as payment_services
    payment = get_object_or_404(Payment, pk=pk)
    try:
        payment_services.refund_payment_record(payment, user=request.user)
    except payment_services.PaymentError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Refund انجام شد.")
    return redirect("dashboard:payment_list")




# ═════════ Categories (در پنل ادمین) ═════════
@staff_required
def category_list(request):
    categories = Category.objects.annotate(
        product_count=Count("products"),
    ).order_by("sort_order", "name")
    return render(request, "dashboard/admin_categories.html", {"categories": categories})


@staff_required
@require_http_methods(["GET", "POST"])
def category_form(request, pk=None):
    category = get_object_or_404(Category, pk=pk) if pk else None
    form = CategoryAdminForm(request.POST or None, request.FILES or None, instance=category)

    if request.method == "POST" and form.is_valid():
        obj = form.save()
        messages.success(request, "دسته‌بندی ذخیره شد.")
        return redirect("dashboard:category_list")

    return render(request, "dashboard/admin_category_form.html", {
        "form": form, "category": category,
    })


# ═════════ Site Settings (در پنل ادمین) ═════════
@staff_required
@require_http_methods(["GET", "POST"])
def site_settings_panel(request):
    from django.core.cache import cache
    from apps.core.models import SiteSettings
    obj = SiteSettings.get_solo()
    form = SiteSettingsPanelForm(request.POST or None, request.FILES or None, instance=obj)

    if request.method == "POST" and form.is_valid():
        form.save()
        cache.delete("site_settings_singleton")
        messages.success(request, "تنظیمات سایت به‌روز شد.")
        return redirect("dashboard:site_settings")

    return render(request, "dashboard/admin_settings.html", {
        "form": form, "settings_obj": obj,
    })


# ═════════ Misc ═════════
@staff_required
def sms_log(request):
    qs = SMSLog.objects.select_related("user").order_by("-created_at")
    page = Paginator(qs, 30).get_page(request.GET.get("page"))
    return render(request, "dashboard/admin_sms.html", {"page": page})


@staff_required
def audit_log(request):
    qs = AuditLog.objects.select_related("user").order_by("-created_at")
    page = Paginator(qs, 30).get_page(request.GET.get("page"))
    return render(request, "dashboard/admin_audit.html", {"page": page})


@staff_required
def security_events(request):
    from apps.accounts.models import SecurityEvent
    qs = SecurityEvent.objects.select_related("user").order_by("-created_at")
    etype = request.GET.get("type")
    if etype:
        qs = qs.filter(event_type=etype)
    page = Paginator(qs, 40).get_page(request.GET.get("page"))
    return render(request, "dashboard/admin_security_events.html", {
        "page": page, "etype": etype, "type_choices": SecurityEvent.TYPE_CHOICES,
    })


@staff_required
def reports(request):
    end = timezone.now().date()
    start = end - timedelta(days=30)
    revenue = Order.objects.filter(
        payment_status=Order.PAYMENT_PAID, paid_at__date__range=(start, end),
    ).aggregate(t=Sum("total_amount"))["t"] or 0
    return render(request, "dashboard/admin_reports.html", {
        "start": start, "end": end, "revenue": revenue,
        "expenses": list(erp_services.expense_summary(start, end)),
        "purchases": list(erp_services.purchase_summary(start, end)),
    })


@staff_required
def notifications(request):
    qs = request.user.admin_notifications.order_by("-created_at")[:50]
    for n in qs:
        dash_services.mark_notification_read(n)
    return render(request, "dashboard/admin_notifications.html", {"notifications": qs})


@login_required
def user_home(request):
    return render(request, "dashboard/user.html", {
        "recent_orders": Order.objects.filter(user=request.user).order_by("-created_at")[:5],
        "address_count": Address.objects.filter(user=request.user).count(),
        "loyalty": LoyaltyAccount.objects.filter(user=request.user).first(),
    })
