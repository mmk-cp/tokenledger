"""Settings shared by all TokenLedger environments."""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parents[2]

env = environ.Env(
    DEBUG=(bool, False),
    DB_CONN_MAX_AGE=(int, 60),
    DB_PORT=(int, 3306),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="unsafe-development-secret-key")
API_KEY_ENCRYPTION_KEY = env("API_KEY_ENCRYPTION_KEY", default="")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

DJANGO_APPS = [
    "unfold.apps.BasicAppConfig",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.inlines",
    "config.apps.TokenLedgerAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

LOCAL_APPS = [
    "apps.core.apps.CoreConfig",
    "apps.providers.apps.ProvidersConfig",
    "apps.wallets.apps.WalletsConfig",
    "apps.customers.apps.CustomersConfig",
    "apps.credits.apps.CreditsConfig",
    "apps.transactions.apps.TransactionsConfig",
    "apps.currencies.apps.CurrenciesConfig",
    "apps.billing.apps.BillingConfig",
    "apps.customer_credentials.apps.CustomerCredentialsConfig",
]

INSTALLED_APPS = DJANGO_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.core.middleware.AuditUserMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": env("DB_NAME"),
        "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST"),
        "PORT": env.int("DB_PORT", default=3306),
        "CONN_MAX_AGE": env.int("DB_CONN_MAX_AGE", default=60),
        "OPTIONS": {"charset": "utf8mb4"},
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"
LANGUAGES = [("en", "English")]
TIME_ZONE = env("TIME_ZONE", default="UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "core.User"

UNFOLD = {
    "SITE_TITLE": "TokenLedger Administration",
    "SITE_HEADER": "TokenLedger",
    "SITE_SUBHEADER": "AI API credit cost management",
    "SITE_SYMBOL": "account_balance_wallet",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": False,
    "SHOW_LANGUAGES": False,
    "DASHBOARD_CALLBACK": "apps.core.admin.dashboard_callback",
    "COLORS": {
        "primary": {
            "50": "oklch(98.4% 0.014 180.72)",
            "100": "oklch(95.3% 0.051 180.801)",
            "200": "oklch(91% 0.096 180.426)",
            "300": "oklch(85.5% 0.138 181.071)",
            "400": "oklch(77.7% 0.152 181.912)",
            "500": "oklch(70.4% 0.14 182.503)",
            "600": "oklch(60% 0.118 184.704)",
            "700": "oklch(51.1% 0.096 186.391)",
            "800": "oklch(43.7% 0.078 188.216)",
            "900": "oklch(38.6% 0.063 188.416)",
            "950": "oklch(27.7% 0.046 192.524)",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
    },
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": env("LOG_LEVEL", default="INFO"),
    },
}
