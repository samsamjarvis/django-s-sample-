from django.urls import path
from . import views

app_name = "dashboard"
urlpatterns = [
    path("login/", views.admin_login_redirect, name="login_redirect"),
    path("", views.admin_home, name="home"),

    # Products
    path("products/", views.product_list, name="product_list"),
    path("products/new/", views.product_form, name="product_create"),
    path("products/<int:pk>/edit/", views.product_form, name="product_edit"),
    path("products/<int:pk>/images/<int:img_id>/delete/", views.product_image_delete, name="product_image_delete"),
    path("products/<int:pk>/images/<int:img_id>/main/", views.product_image_set_main, name="product_image_set_main"),

    # Categories
    path("categories/", views.category_list, name="category_list"),
    path("categories/new/", views.category_form, name="category_create"),
    path("categories/<int:pk>/edit/", views.category_form, name="category_edit"),

    # Site Settings (لوگو، Hero، ...)
    path("settings/", views.site_settings_panel, name="site_settings"),

    # Orders
    path("orders/", views.order_list, name="order_list"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
    path("orders/<int:pk>/action/<str:action>/", views.order_action, name="order_action"),

    # Customers
    path("customers/", views.customer_list, name="customer_list"),
    path("customers/<int:pk>/", views.customer_detail, name="customer_detail"),

    # Inventory
    path("inventory/", views.inventory_list, name="inventory_list"),
    path("inventory/<int:product_id>/adjust/", views.stock_adjust, name="stock_adjust"),

    # Payments
    path("payments/", views.payment_list, name="payment_list"),
    path("payments/settings/", views.payment_settings, name="payment_settings"),
    path("payments/<int:pk>/reconcile/", views.payment_reconcile, name="payment_reconcile"),
    path("payments/<int:pk>/refund/", views.payment_refund, name="payment_refund"),

    # Misc
    path("sms/", views.sms_log, name="sms_log"),
    path("audit/", views.audit_log, name="audit_log"),
    path("security/", views.security_events, name="security_events"),
    path("reports/", views.reports, name="reports"),
    path("notifications/", views.notifications, name="notifications"),
]
