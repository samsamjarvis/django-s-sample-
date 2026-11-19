from django.urls import path
from . import views

app_name = "payment"
urlpatterns = [
    path("initiate/<int:order_id>/", views.initiate, name="initiate"),
    path("verify/", views.verify, name="verify"),
]