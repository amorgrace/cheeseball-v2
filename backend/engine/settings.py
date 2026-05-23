
import os
import sys
from datetime import timedelta
import datetime
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv






BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ImproperlyConfigured("SECRET_KEY is not set in the environment.")


DEBUG = os.getenv("DEBUG", "True").lower() == "true"

ALLOWED_HOSTS = [host.strip() for host in os.getenv("ALLOWED_HOSTS", "").split(",") if host.strip()]
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if origin.strip()]
CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
CSRF_TRUSTED_ORIGINS = [
    "https://cheeseballapp.com",
    "https://www.cheeseballapp.com",
    "https://*.vercel.app",
]




INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    "anymail",
    "corsheaders",
    "ninja_jwt",
    "ninja_jwt.token_blacklist",
    "authenticator",
    "rates",
    "broker",
    "payouts",
    "wallets",
    "payments",
    "kyc",
]

AUTH_USER_MODEL = "authenticator.CustomUser"


NINJA_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": True,
}


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    "corsheaders.middleware.CorsMiddleware",
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    "whitenoise.middleware.WhiteNoiseMiddleware",
]

STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")


ROOT_URLCONF = 'engine.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'engine.wsgi.application'






database_url = os.environ.get("DATABASE_URL")
if "test" in sys.argv:
    database_url = os.environ.get("TEST_DATABASE_URL", database_url)

DATABASES = {
    "default": dj_database_url.parse(database_url)
}




AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]





LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True





STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

BINANCE_PRICE_URL_TEMPLATE = os.getenv(
    "BINANCE_PRICE_URL_TEMPLATE",
    "https://api.binance.com/api/v3/ticker/price?symbol={symbol}",
)
BTC_NGN_RATE_FALLBACK = os.getenv("BTC_NGN_RATE_FALLBACK", "150000000")
ETH_NGN_RATE_FALLBACK = os.getenv("ETH_NGN_RATE_FALLBACK", "5000000")
USDT_NGN_RATE_FALLBACK = os.getenv("USDT_NGN_RATE_FALLBACK", "1600")
USD_NGN_EXCHANGE_RATE = os.getenv("USD_NGN_EXCHANGE_RATE", "1600")
BUY_MARKUP_PERCENT = os.getenv("BUY_MARKUP_PERCENT", "3.0")
SELL_MARKUP_PERCENT = os.getenv("SELL_MARKUP_PERCENT", "2.0")
QUOTE_TTL_MINUTES = int(os.getenv("QUOTE_TTL_MINUTES", "10"))

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "")
PAYSTACK_PUBLIC_KEY = os.getenv("PAYSTACK_PUBLIC_KEY", "")
PAYSTACK_WEBHOOK_SECRET = os.getenv("PAYSTACK_WEBHOOK_SECRET", PAYSTACK_SECRET_KEY)
PAYSTACK_CURRENCY = os.getenv("PAYSTACK_CURRENCY", "NGN")
PAYSTACK_CHARGE_URL = os.getenv("PAYSTACK_CHARGE_URL", "https://api.paystack.co/charge")
PAYSTACK_BANK_TRANSFER_EXPIRES_MINUTES = int(os.getenv("PAYSTACK_BANK_TRANSFER_EXPIRES_MINUTES", "30"))

ANYMAIL = {
    "MAILTRAP_API_TOKEN": os.getenv("MAILTRAP_API_TOKEN", ""),
    "MAILTRAP_SANDBOX_ID": os.getenv("MAILTRAP_SANDBOX_ID") or None,
}
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "anymail.backends.mailtrap.EmailBackend")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "CheeseBall Support <support@www.cheeseballapp.com>")

BANK_ACCOUNT_NAME = os.getenv("BANK_ACCOUNT_NAME", "CheeseBall Limited")
BANK_ACCOUNT_NUMBER = os.getenv("BANK_ACCOUNT_NUMBER", "0000000000")
BANK_NAME = os.getenv("BANK_NAME", "Demo Bank")
BROKER_BTC_WALLET_ADDRESS = os.getenv("BROKER_BTC_WALLET_ADDRESS", "")
BROKER_ETH_WALLET_ADDRESS = os.getenv("BROKER_ETH_WALLET_ADDRESS", "")
BROKER_USDT_WALLET_ADDRESS = os.getenv("BROKER_USDT_WALLET_ADDRESS", "")
