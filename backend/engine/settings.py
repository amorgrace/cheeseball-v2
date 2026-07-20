import os
import sys
from datetime import timedelta
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ImproperlyConfigured("SECRET_KEY is not set in the environment.")
if len(SECRET_KEY.encode()) < 32:
    raise ImproperlyConfigured(
        "SECRET_KEY is too short for JWT signing (must be at least 32 bytes). "
        "Generate a new one with: python -c \"import secrets; print(secrets.token_hex(32))\""
    )

DEBUG = os.getenv("DEBUG", "True").lower() == "true"

ALLOWED_HOSTS = [host.strip() for host in os.getenv("ALLOWED_HOSTS", "").split(",") if host.strip()]
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if origin.strip()]
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.vercel\.app$",
    r"^http://localhost:3000$",
]
CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
CSRF_TRUSTED_ORIGINS = [
    "https://cheeseballapp.com",
    "https://www.cheeseballapp.com",
    "https://*.vercel.app",
    "http://localhost:3000",
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
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
    "quidax",
    "notifications",
    "transfers",
    "giftcards",
    "hd_wallets",
    "tatum",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "engine.urls"
WSGI_APPLICATION = "engine.wsgi.application"
ASGI_APPLICATION = "engine.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

database_url = os.environ.get("DATABASE_URL")
if "test" in sys.argv:
    database_url = os.environ.get("TEST_DATABASE_URL", database_url)
DATABASES = {"default": dj_database_url.parse(database_url)}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}

AUTH_USER_MODEL = "authenticator.CustomUser"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Optional JWT lifetimes (used by django-ninja-jwt defaults)
NINJA_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    # Explicitly pass SECRET_KEY so PyJWT never falls back to a short/wrong key.
    "SIGNING_KEY": SECRET_KEY,
}

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
PAYSTACK_TRANSFER_RECIPIENT_URL = os.getenv("PAYSTACK_TRANSFER_RECIPIENT_URL", "https://api.paystack.co/transferrecipient")
PAYSTACK_TRANSFER_URL = os.getenv("PAYSTACK_TRANSFER_URL", "https://api.paystack.co/transfer")

QUIDAX_API_BASE_URL = os.getenv("QUIDAX_API_BASE_URL", "https://openapi.quidax.io/exchange-open-api/api/v1")
QUIDAX_API_KEY = os.getenv("QUIDAX_API_KEY", "")
QUIDAX_SECRET_KEY = os.getenv("QUIDAX_SECRET_KEY", "")
QUIDAX_WEBHOOK_SECRET = os.getenv("QUIDAX_WEBHOOK_SECRET", "")

CRON_SECRET = os.getenv("CRON_SECRET", "")

# ---------------------------------------------------------------------------
# CRYPTO PROVIDER FEATURE FLAG
# ---------------------------------------------------------------------------
# Set to "hd_tatum" to use HD wallet + Tatum monitoring.
# Set to "quidax" to keep the existing Quidax flow (default during dual-run).
CRYPTO_PROVIDER = os.getenv("CRYPTO_PROVIDER", "hd_tatum")

# ---------------------------------------------------------------------------
# TATUM — monitoring only
# ---------------------------------------------------------------------------
TATUM_API_KEY = os.getenv("TATUM_API_KEY", "")
TATUM_WEBHOOK_SECRET = os.getenv("TATUM_WEBHOOK_SECRET", "")
TATUM_WEBHOOK_URL = os.getenv("TATUM_WEBHOOK_URL", "")
TATUM_API_BASE_URL = os.getenv("TATUM_API_BASE_URL", "https://api.tatum.io/v3")

# ---------------------------------------------------------------------------
# HD WALLET — xpub keys per chain (public keys only — xpriv lives on signer)
# ---------------------------------------------------------------------------
HD_WALLET_XPUB_ETHEREUM = os.getenv("HD_WALLET_XPUB_ETHEREUM", "")
HD_WALLET_XPUB_BSC = os.getenv("HD_WALLET_XPUB_BSC", "")
HD_WALLET_XPUB_POLYGON = os.getenv("HD_WALLET_XPUB_POLYGON", "")
HD_WALLET_XPUB_CELO = os.getenv("HD_WALLET_XPUB_CELO", "")
HD_WALLET_XPUB_TRON = os.getenv("HD_WALLET_XPUB_TRON", "")
HD_WALLET_XPUB_SOLANA = os.getenv("HD_WALLET_XPUB_SOLANA", "")
HD_WALLET_XPUB_TON = os.getenv("HD_WALLET_XPUB_TON", "")
HD_WALLET_XPUB_BITCOIN = os.getenv("HD_WALLET_XPUB_BITCOIN", "")

# Master / hot wallet addresses (treasury sweep targets)
MASTER_WALLET_ADDRESS_ETHEREUM = os.getenv("MASTER_WALLET_ADDRESS_ETHEREUM", "")
MASTER_WALLET_ADDRESS_BSC = os.getenv("MASTER_WALLET_ADDRESS_BSC", "")
MASTER_WALLET_ADDRESS_POLYGON = os.getenv("MASTER_WALLET_ADDRESS_POLYGON", "")
MASTER_WALLET_ADDRESS_CELO = os.getenv("MASTER_WALLET_ADDRESS_CELO", "")
MASTER_WALLET_ADDRESS_TRON = os.getenv("MASTER_WALLET_ADDRESS_TRON", "")
MASTER_WALLET_ADDRESS_SOLANA = os.getenv("MASTER_WALLET_ADDRESS_SOLANA", "")
MASTER_WALLET_ADDRESS_TON = os.getenv("MASTER_WALLET_ADDRESS_TON", "")
MASTER_WALLET_ADDRESS_BITCOIN = os.getenv("MASTER_WALLET_ADDRESS_BITCOIN", "")

# Signer service (handles private key access — NOT on Vercel)
HD_WALLET_SIGNER_URL = os.getenv("HD_WALLET_SIGNER_URL", "")
HD_WALLET_SIGNER_SECRET = os.getenv("HD_WALLET_SIGNER_SECRET", "")



# Auth cookie settings for JWT in HttpOnly cookies
AUTH_COOKIE_SECURE = os.getenv("AUTH_COOKIE_SECURE", "true").lower() == "true"
AUTH_COOKIE_SAMESITE = os.getenv("AUTH_COOKIE_SAMESITE", "Lax")
AUTH_COOKIE_DOMAIN = os.getenv("AUTH_COOKIE_DOMAIN") or None
AUTH_COOKIE_PATH = os.getenv("AUTH_COOKIE_PATH", "/")
AUTH_ACCESS_COOKIE_MAX_AGE = int(os.getenv("AUTH_ACCESS_COOKIE_MAX_AGE", "1800"))
AUTH_REFRESH_COOKIE_MAX_AGE = int(os.getenv("AUTH_REFRESH_COOKIE_MAX_AGE", "604800"))

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

# Quidax merchant wallet addresses for sweeping sub-account funds
MERCHANT_USDT_ADDRESS = os.getenv("MERCHANT_USDT_ADDRESS", "")
MERCHANT_BTC_ADDRESS = os.getenv("MERCHANT_BTC_ADDRESS", "")
MERCHANT_ETH_ADDRESS = os.getenv("MERCHANT_ETH_ADDRESS", "")


# ------------------------------------------------------------------------------
# LOGGING CONFIGURATION
# ------------------------------------------------------------------------------
LOG_DIR = BASE_DIR / "logs"

# Detect if we can write to the filesystem (Vercel's /var/task is read-only)
_USE_FILE_LOGGING = True
try:
    LOG_DIR.mkdir(exist_ok=True)
except OSError:
    _USE_FILE_LOGGING = False

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose" if not _USE_FILE_LOGGING else "simple",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
    },
}

# Add file handlers only when the filesystem is writable (local dev)
if _USE_FILE_LOGGING:
    LOGGING["handlers"]["file"] = {
        "level": "INFO",
        "class": "logging.handlers.RotatingFileHandler",
        "filename": LOG_DIR / "cheeseball.log",
        "maxBytes": 1024 * 1024 * 5,  # 5 MB
        "backupCount": 5,
        "formatter": "verbose",
    }
    LOGGING["handlers"]["django_file"] = {
        "level": "ERROR",
        "class": "logging.handlers.RotatingFileHandler",
        "filename": LOG_DIR / "django_errors.log",
        "maxBytes": 1024 * 1024 * 5,  # 5 MB
        "backupCount": 5,
        "formatter": "verbose",
    }
    LOGGING["loggers"]["django"]["handlers"].append("django_file")
    LOGGING["loggers"]["django.request"]["handlers"].append("django_file")
    LOGGING["loggers"][""]["handlers"].append("file")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

