"""SEO context processor — مقادیر پیش‌فرض سئو در همهٔ قالب‌ها."""
from django.conf import settings


def seo_context(request):
    base = f"{settings.SITE_PROTOCOL}://{settings.SITE_DOMAIN}"
    return {
        "SEO_SITE_NAME": settings.SITE_NAME,
        "SEO_BASE_URL": base,
        "SEO_DEFAULT_DESCRIPTION": settings.SEO_DEFAULT_DESCRIPTION,
        "SEO_DEFAULT_KEYWORDS": settings.SEO_DEFAULT_KEYWORDS,
        "SEO_DEFAULT_IMAGE": (
            f"{base}{settings.SEO_DEFAULT_IMAGE}"
            if getattr(settings, "SEO_DEFAULT_IMAGE", "") else ""
        ),
        "SEO_NOINDEX": getattr(request, "seo_noindex", False),
    }
