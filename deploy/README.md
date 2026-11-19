# Silver — Django Jewelry Shop

فروشگاه آنلاین نقره — معماری MVT، پنل ادمین اختصاصی با تم لندینگ (PDF)، پرداخت زرین‌پال، sms.ir، 2FA، CRM، ERP، SEO، امنیت کامل. فرانت: HTML/CSS/JS خالص (بدون Bootstrap، بدون REST). دیتابیس: PostgreSQL + رمزنگاری فیلدهای حساس با Fernet.

## Stack
- Django 4.2 LTS (MVT)
- PostgreSQL 16
- Redis 7 (cache/session)
- Gunicorn + Nginx
- Docker + docker-compose
- Zarinpal + sms.ir + pyotp

## راه‌اندازی

```bash
cp .env.example .env
# SECRET_KEY، ENCRYPTION_KEY، ZARINPAL_MERCHANT_ID، SMSIR_API_KEY را پر کن

python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

docker compose up --build -d
docker compose exec web python backend/manage.py createsuperuser