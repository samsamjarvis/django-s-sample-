from django.urls import path
from . import views

app_name = "accounts"
urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("signup/", views.signup_view, name="signup"),
    path("profile/", views.profile_view, name="profile"),
    path("two-factor/", views.two_factor_verify, name="two_factor_verify"),

    path("password/change/", views.password_change, name="password_change"),
    path("password/reset/", views.password_reset_request, name="password_reset_request"),
    path("password/reset/verify/", views.password_reset_verify, name="password_reset_verify"),
    path("password/reset/confirm/", views.password_reset_confirm, name="password_reset_confirm"),

    path("2fa/setup/", views.twofa_setup, name="twofa_setup"),
    path("2fa/setup/confirm/", views.twofa_setup_confirm, name="twofa_setup_confirm"),
    path("2fa/recovery-codes/", views.twofa_recovery_codes, name="twofa_recovery_codes"),
    path("2fa/manage/", views.twofa_manage, name="twofa_manage"),
    path("2fa/disable/", views.twofa_disable, name="twofa_disable"),
    path("2fa/regenerate-recovery/", views.twofa_regenerate_recovery, name="twofa_regenerate_recovery"),
]