from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from .models import Category, Product


def _sort_qs(qs, sort: str):
    if sort == "price_asc":
        return qs.order_by("price")
    if sort == "price_desc":
        return qs.order_by("-price")
    return qs.order_by("-created_at")


def product_list(request):
    qs = (
        Product.objects.filter(is_active=True)
        .select_related("category").prefetch_related("images")
    )
    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(name__icontains=q)
    sort = request.GET.get("sort", "newest")
    page = Paginator(_sort_qs(qs, sort), 12).get_page(request.GET.get("page"))
    categories = (
        Category.objects.filter(is_active=True, parent__isnull=True)
        .order_by("sort_order", "name")
    )
    return render(request, "products/list.html", {
        "page": page, "categories": categories, "q": q, "sort": sort,
    })


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    qs = (
        Product.objects.filter(is_active=True, category=category)
        .select_related("category").prefetch_related("images")
    )
    page = Paginator(_sort_qs(qs, request.GET.get("sort", "newest")), 12) \
        .get_page(request.GET.get("page"))
    return render(request, "products/category.html", {
        "category": category, "page": page,
        "children": category.children.filter(is_active=True),
    })


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related("category").prefetch_related("images"),
        slug=slug, is_active=True,
    )
    related = (
        Product.objects.filter(is_active=True, category=product.category)
        .exclude(id=product.id)
        .select_related("category").prefetch_related("images")[:4]
    )
    return render(request, "products/detail.html", {
        "product": product, "related": related,
    })