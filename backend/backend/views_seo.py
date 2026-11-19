"""robots.txt + error handlers."""
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render


def robots_txt(request):
    lines = [
        "User-agent: *",
        "Allow: /",
        f"Sitemap: {settings.SITE_PROTOCOL}://{settings.SITE_DOMAIN}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def handler403(request, exception=None):
    return render(request, "403.html", status=403)


def handler404(request, exception=None):
    return render(request, "404.html", status=404)


def handler500(request):
    return render(request, "500.html", status=500)