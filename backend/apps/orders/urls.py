from django.urls import path
from . import views

app_name = "orders"
urlpatterns = [
    path("", views.order_list, name="list"),
    path("checkout/", views.checkout, name="checkout"),
    path("<str:order_number>/", views.order_detail, name="detail"),
    path("<str:order_number>/cancel/", views.order_cancel, name="cancel"),
]