"""Root URL config — همه include()ها lazy (فقط در دسترس‌شدن URL)."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from backend.views_seo import robots_txt
from backend.sitemaps import sitemap_index

urlpatterns = [
    # Public
    path("", include("apps.core.urls", namespace="core")),
    path("auth/", include("apps.accounts.urls", namespace="accounts")),
    path("products/", include("apps.products.urls", namespace="products")),
    path("orders/", include("apps.orders.urls", namespace="orders")),
    path("cart/", include("apps.orders.urls_cart", namespace="cart")),
    path("payment/", include("apps.payment.urls", namespace="payment")),
    path("crm/", include("apps.crm.urls", namespace="crm")),
    path("customers/", include("apps.customers.urls", namespace="customers")),

    # Dashboards
    path("panel/", include("apps.dashboard.urls", namespace="dashboard")),
    path("my/", include("apps.dashboard.user_urls", namespace="user_dashboard")),

    # Django admin (obfuscated)
    #path(settings.ADMIN_URL, admin.site.urls),

    # SEO
    path("sitemap.xml", sitemap_index, name="sitemap_index"),
    path("robots.txt", robots_txt, name="robots_txt"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

handler403 = "backend.views_seo.handler403"
handler404 = "backend.views_seo.handler404"
handler500 = "backend.views_seo.handler500"