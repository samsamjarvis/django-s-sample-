
### `SECURITY.md`

```markdown
# Security Policy

## Report
security@silver.example.com — لطفاً Issue عمومی باز نکن.

## Measures
- TLS + HSTS + CSP + X-Frame + nosniff (Nginx)
- CSRF secure، SameSite=Lax
- CORS محدود به originهای env
- Fernet field-level encryption (DB)
- HMAC-SHA256 signing برای payloadهای حساس
- django-axes (۵ تلاش → ۱۵ دقیقه lock)
- Request-ID tracing + audit log
- ErrorHandler — هرگز stack trace به کلاینت
- AdminAccessMiddleware — hide admin login