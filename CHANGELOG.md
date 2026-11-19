# Changelog

## [0.1.0] — Phase 1: Foundation
### Added
- ساختار کامل پروژه مطابق tree (14 app + nested backend package)
- settings.py: security, logging, Redis cache/session, CORS/CSRF, axes
- Fernet field-level encryption + HMAC helpers
- RequestLoggingMiddleware + ErrorHandlingMiddleware + AdminAccessMiddleware
- Nginx (HTTP→HTTPS, gzip, upstream keepalive) + security headers
- Dockerfile + docker-compose (prod & dev) + entrypoint
- requirements، .env.example، README، SECURITY، LICENCE
- اسکلت کامل ۱۴ اپ (بدون منطق — فازهای ۲-۴)
- base.html + home.html + 403/404/500 placeholder