"""Core views — home, about, faq, contact, page."""
from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.products.models import Category, Product
from .forms import ContactForm
from .models import FAQ, Page


def home(request):
    categories = (
        Category.objects.filter(is_active=True, parent__isnull=True)
        .order_by("sort_order", "name")[:12]
    )
    new_products = (
        Product.objects.filter(is_active=True, is_new=True)
        .select_related("category").prefetch_related("images")[:8]
    )
    featured = (
        Product.objects.filter(is_active=True, is_featured=True)
        .select_related("category").prefetch_related("images")[:8]
    )
    faqs = FAQ.objects.filter(is_active=True)[:6]
    return render(request, "home.html", {
        "categories": categories,
        "new_products": new_products,
        "featured_products": featured,
        "faqs": faqs,
    })


def about(request):
    try:
        page = Page.objects.get(slug="about", is_published=True)
    except Page.DoesNotExist:
        page = None
    return render(request, "core/about.html", {"page": page})


def faq(request):
    return render(request, "core/faq.html", {"faqs": FAQ.objects.filter(is_active=True)})


@require_http_methods(["GET", "POST"])
def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "پیام شما ارسال شد.")
        return redirect("core:contact")
    return render(request, "core/contact.html", {"form": form})


def page_detail(request, slug):
    page = get_object_or_404(Page, slug=slug, is_published=True)
    return render(request, "core/page.html", {"page": page})
