"""Sitemap placeholder — فاز ۸ کامل می‌شود."""
from django.http import HttpResponse


def sitemap_index(request):
    scheme = request.scheme
    host = request.get_host()
    urls = [f"{scheme}://{host}/", f"{scheme}://{host}/products/"]
    body = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for u in urls:
        body.append(f"<url><loc>{u}</loc></url>")
    body.append("</urlset>")
    return HttpResponse("\n".join(body), content_type="application/xml")