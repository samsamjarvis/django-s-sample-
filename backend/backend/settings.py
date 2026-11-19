"""
Silver — Django settings.
تنظیمات یکپارچه از ۱۰ فاز. Production-ready با fallbackهای امن.
همه secrets از .env خوانده می‌شوند.
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import environ

# ══════════════════════════════════════════════════════════════════
# Paths & Env
# ══════════════════════════════════════════════════════════════════
# settings.py path: backend/backend/settings.py → parents[2] = project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASE_DIR = PROJECT_ROOT / "backend"

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(str(PROJECT_ROOT / ".env"))


# ══════════════════════════════════════════════════════════════════
# Core
# ══════════════════════════════════════════════════════════════════
SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

APP_VERSION = env("APP_VERSION", default="1.0.0")


# ══════════════════════════════════════════════════════════════════
# Applications
# ══════════════════════════════════════════════════════════════════
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "django.contrib.humanize",
]

THIRD_PARTY_APPS = [
    "corsheaders",
    "axes",
]

LOCAL_APPS = [
    "apps.core",
    "apps.accounts",
    "apps.customers",
    "apps.products",
    "apps.inventory",
    "apps.orders",
    "apps.payment",
    "apps.crm",
    "apps.erp",
    "apps.marketplace",
    "apps.dashboard",
    "apps.seo",
    "apps.sms",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS


# ══════════════════════════════════════════════════════════════════
# Middleware
# ══════════════════════════════════════════════════════════════════
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "backend.middleware.SeoMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",
    "backend.middleware.AdminAccessMiddleware",
    "backend.middleware.SessionPasswordMiddleware",
    "backend.middleware.RequestLoggingMiddleware",
    "backend.middleware.ErrorHandlingMiddleware",
]


# ══════════════════════════════════════════════════════════════════
# URLs / WSGI / ASGI
# ══════════════════════════════════════════════════════════════════
ROOT_URLCONF = "backend.urls"
WSGI_APPLICATION = "backend.wsgi.application"
ASGI_APPLICATION = "backend.asgi.application"


# ══════════════════════════════════════════════════════════════════
# Templates
# ══════════════════════════════════════════════════════════════════
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [str(PROJECT_ROOT / "frontend" / "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.site_context",
                "apps.seo.context_processors.seo_context",
            ],
        },
    },
]


# ══════════════════════════════════════════════════════════════════
# Database
# ══════════════════════════════════════════════════════════════════
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME"),
        "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST", default="localhost"),
        "PORT": env("DB_PORT", default="5432"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {"connect_timeout": 10},
    }
}


# ══════════════════════════════════════════════════════════════════
# Authentication
# ══════════════════════════════════════════════════════════════════
AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

LOGIN_URL = "/auth/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ══════════════════════════════════════════════════════════════════
# i18n / Time
# ══════════════════════════════════════════════════════════════════
LANGUAGE_CODE = "fa-ir"
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True


# ══════════════════════════════════════════════════════════════════
# Static & Media
# ══════════════════════════════════════════════════════════════════
STATIC_URL = "/static/"
STATICFILES_DIRS = [
    str(PROJECT_ROOT / "frontend" / "static"),
    str(BASE_DIR / "static"),
]
STATIC_ROOT = str(BASE_DIR / "staticfiles")

MEDIA_URL = "/media/"
MEDIA_ROOT = str(BASE_DIR / "media")

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
WHITENOISE_MAX_AGE = 31536000

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ══════════════════════════════════════════════════════════════════
# Cache & Session backend
# ══════════════════════════════════════════════════════════════════
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "silver-local",
        
        "TIMEOUT": 300,
        "KEY_PREFIX": "silver",
    }
}


SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_CACHE_ALIAS = "default"


# ══════════════════════════════════════════════════════════════════
# ═══════════════ فاز ۶: Security Hardening ═══════════════
# ══════════════════════════════════════════════════════════════════

# ─── Session ───
# طول عمر ۱۴ روز برای کاربر عادی — ادمین ۸ ساعت (در session_security.py اعمال می‌شود)
SESSION_COOKIE_AGE = env.int("SESSION_COOKIE_AGE", default=14 * 24 * 3600)
ADMIN_SESSION_AGE = env.int("ADMIN_SESSION_AGE", default=8 * 3600)
SESSION_EXPIRE_AT_BROWSER_CLOSE = env.bool("SESSION_EXPIRE_AT_BROWSER_CLOSE", default=False)
# ذخیره session در هر درخواست — برای sync بین tabها و به‌روزرسانی stamp
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_NAME = "silver_session"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=not DEBUG)

# ─── CSRF ───
CSRF_COOKIE_AGE = env.int("CSRF_COOKIE_AGE", default=14 * 24 * 3600)
CSRF_COOKIE_NAME = "silver_csrf"
# اگر True، جاوااسکریپت نمی‌تواند به کوکی دسترسی داشته باشد — برای فرم‌های JS نیاز به False
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=not DEBUG)
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
#CSRF_FAILURE_VIEW = "backend.views_seo.handler403"

# ─── Security Headers ───
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=not DEBUG)
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# ─── CORS ───
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
CORS_ALLOW_HEADERS = [
    "accept", "authorization", "content-type", "origin", "user-agent",
    "x-csrftoken", "x-requested-with", "x-encrypted", "x-request-id",
]

# ─── Axes — login brute-force throttling ───
AXES_FAILURE_LIMIT = env.int("AXES_FAILURE_LIMIT", default=5)
AXES_COOLOFF_TIME = timedelta(minutes=env.int("AXES_COOLOFF_MINUTES", default=15))
AXES_LOCKOUT_CALLABLE = "backend.security.axes_lockout_response"
AXES_RESET_ON_SUCCESS = True
# Django admin lockout نمی‌شود (جلوگیری از قفل‌شدن ادمین در شرایط اضطراری)
AXES_ENABLE_ADMIN = False
AXES_VERBOSE = DEBUG
# تعداد proxyهای جلوی اپ — ۱ = nginx
# اگر nginx با real_ip module تنظیم شده، 0 بگذار؛ اگر X-Forwarded-For خام پاس می‌شود، 1
AXES_IPWARE_PROXY_COUNT = env.int("AXES_IPWARE_PROXY_COUNT", default=1)
AXES_IPWARE_META_PRECEDENCE_ORDER = (
    "HTTP_X_FORWARDED_FOR",
    "REMOTE_ADDR",
)

# ─── Rate limiting (django-ratelimit) ───
# نکته: ما در core/ratelimit.py از decorator خودمان استفاده می‌کنیم،
# اما این تنظیمات برای زمانی که decorator استاندارد django-ratelimit بلااستفاده ماند،
# پاسخ fallback را تعیین می‌کند.
RATELIMIT_USE_CACHE = "default"
RATELIMIT_VIEW = "backend.views_seo.handler429"
# تعداد درخواست‌ها در پنجره — نه اینجا؛ در decorator تعریف می‌شود

# ─── 2FA ───
TWO_FACTOR_ENABLED = env.bool("TWO_FACTOR_ENABLED", default=True)
TWO_FACTOR_RECOVERY_CODE_COUNT = 10
TWO_FACTOR_TOTP_WINDOW = 1              # ±30 ثانیه انحراف
TWO_FACTOR_PENDING_TIMEOUT = 300        # ۵ دقیقه — pending session بعد از لاگین
TWO_FACTOR_OTP_TTL_MINUTES = 2          # انقضای OTP پیامکی

# ─── Encryption ───
ENCRYPTION_KEY = env("ENCRYPTION_KEY", default="")
FIELD_ENCRYPTION_ENABLED = env.bool("FIELD_ENCRYPTION_ENABLED", default=True)

# ─── Admin URL obfuscation ───
ADMIN_URL = env("ADMIN_URL", default="admin/")
ADMIN_LOGIN_ENABLED = env.bool("ADMIN_LOGIN_ENABLED", default=True)


# ══════════════════════════════════════════════════════════════════
# 3rd-party — Payment (Zarinpal)
# ══════════════════════════════════════════════════════════════════
PAYMENT_ENABLED = env.bool("PAYMENT_ENABLED", default=True)
ZARINPAL_MERCHANT_ID = env("ZARINPAL_MERCHANT_ID", default="")
ZARINPAL_SANDBOX = env.bool("ZARINPAL_SANDBOX", default=True)
ZARINPAL_CALLBACK_URL = env("ZARINPAL_CALLBACK_URL", default="")


# ══════════════════════════════════════════════════════════════════
# 3rd-party — SMS (sms.ir)
# ══════════════════════════════════════════════════════════════════
SMS_ENABLED = env.bool("SMS_ENABLED", default=True)
SMSIR_API_KEY = env("SMSIR_API_KEY", default="")
SMSIR_LINE_NUMBER = env("SMSIR_LINE_NUMBER", default="")
SMSIR_TEMPLATE_OTP = env("SMSIR_TEMPLATE_OTP", default="100000")
SMSIR_TEMPLATE_ORDER = env("SMSIR_TEMPLATE_ORDER", default="100001")
SMS_OTP_RATE_LIMIT_MINUTES = 10         # ۵ OTP در ۱۰ دقیقه
SMS_OTP_MIN_INTERVAL_SECONDS = 60       # حداقل ۶۰ ثانیه بین دو ارسال


# ══════════════════════════════════════════════════════════════════
# Production validation — fail-fast روی envهای حیاتی
# ══════════════════════════════════════════════════════════════════
if not DEBUG:
    from django.core.exceptions import ImproperlyConfigured

    if PAYMENT_ENABLED and not ZARINPAL_SANDBOX:
        if not ZARINPAL_MERCHANT_ID:
            raise ImproperlyConfigured(
                "ZARINPAL_MERCHANT_ID در production (sandbox=false) الزامی است."
            )
        if not ZARINPAL_CALLBACK_URL:
            raise ImproperlyConfigured(
                "ZARINPAL_CALLBACK_URL در production الزامی است."
            )

    if SMS_ENABLED and not SMSIR_API_KEY:
        raise ImproperlyConfigured(
            "SMSIR_API_KEY در production الزامی است."
        )

    if not ENCRYPTION_KEY or FIELD_ENCRYPTION_ENABLED is False:
        # هشدار — نه خطا (برای اجازه به migration در شرایط خاص)
        import warnings
        warnings.warn(
            "ENCRYPTION_KEY خالی است یا FIELD_ENCRYPTION_ENABLED=False — "
            "رمزنگاری فیلدهای حساس در production غیرفعال است!",
            RuntimeWarning,
        )


# ══════════════════════════════════════════════════════════════════
# Email
# ══════════════════════════════════════════════════════════════════
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Silver <noreply@localhost>")

if DEBUG and not EMAIL_HOST:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"


# ══════════════════════════════════════════════════════════════════
# Site meta
# ══════════════════════════════════════════════════════════════════
SITE_NAME = env("SITE_NAME", default="Silver")
SITE_DOMAIN = env("SITE_DOMAIN", default="localhost")
SITE_PROTOCOL = env("SITE_PROTOCOL", default="http")


# ══════════════════════════════════════════════════════════════════
# SEO (Phase 8)
# ══════════════════════════════════════════════════════════════════
SEO_SITEMAP_CACHE = env.int("SEO_SITEMAP_CACHE", default=3600)
SEO_DEFAULT_DESCRIPTION = (
    "فروشگاه آنلاین نقره Silver — انگشتر، گوشواره، زنجیر، دستبند، "
    "گردنبند، ساعت. ارسال به سراسر ایران، پرداخت امن با زرین‌پال."
)
SEO_DEFAULT_KEYWORDS = "نقره، انگشتر نقره، گوشواره نقره، گردنبند، دستبند، Silver"
SEO_DEFAULT_IMAGE = "/static/images/og-default.jpg"


# ══════════════════════════════════════════════════════════════════
# Logging
# ══════════════════════════════════════════════════════════════════
LOG_DIR = Path(env("LOG_DIR", default=str(BASE_DIR / "logs")))
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_LEVEL = env("LOG_LEVEL", default="INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {process:d} {thread:d} :: {message}",
            "style": "{",
        },
        "simple": {
            "format": "[{asctime}] {levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "app.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 10,
            "formatter": "verbose",
            "encoding": "utf-8",
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "error.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 10,
            "formatter": "verbose",
            "level": "ERROR",
            "encoding": "utf-8",
        },
        "security_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "security.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 10,
            "formatter": "verbose",
            "encoding": "utf-8",
        },
    },
    "root": {"handlers": ["console", "file"], "level": LOG_LEVEL},
    "loggers": {
        "django.request": {
            "handlers": ["console", "error_file"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console", "security_file"],
            "level": "WARNING",
            "propagate": False,
        },
        "silver": {
            "handlers": ["console", "file", "error_file"],
            "level": LOG_LEVEL,
        },
    },
}


# ══════════════════════════════════════════════════════════════════
# Celery (Phase 7)
# ══════════════════════════════════════════════════════════════════
CELERY_BROKER_URL = env("REDIS_URL", default="redis://redis:6379/0")
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

CELERY_BEAT_SCHEDULE = {
    "release-expired-reservations": {
        "task": "apps.inventory.tasks.release_expired_reservations_task",
        "schedule": 300.0,          # هر ۵ دقیقه
    },
    "reconcile-stuck-payments": {
        "task": "apps.payment.tasks.reconcile_stuck_payments_task",
        "schedule": 600.0,          # هر ۱۰ دقیقه
    },
    "poll-sms-delivery": {
        "task": "apps.sms.tasks.poll_delivery_reports_task",
        "schedule": 900.0,          # هر ۱۵ دقیقه
    },
}


# ══════════════════════════════════════════════════════════════════
# Sentry (optional)
# ══════════════════════════════════════════════════════════════════
SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN and not DEBUG:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
        environment="production",
    )


# ══════════════════════════════════════════════════════════════════
# Media/Thumbnails (Phase 10)
# ══════════════════════════════════════════════════════════════════
THUMB_DIR_NAME = "_thumbs"
THUMB_QUALITY_WEBP = 82
THUMB_QUALITY_JPEG = 82


# ══════════════════════════════════════════════════════════════════
# Backup / Maintenance
# ══════════════════════════════════════════════════════════════════
MAINTENANCE_MODE = env.bool("MAINTENANCE_MODE", default=False)