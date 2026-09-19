import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env_int(name, default):
    return int(os.environ.get(name, default))


SECRET_KEY = os.environ.get("TASKDROPBOX_SECRET_KEY", "development-only-not-for-production")
DEBUG = os.environ.get("TASKDROPBOX_DEBUG", "0") == "1"
ALLOWED_HOSTS = [
    item.strip()
    for item in os.environ.get("TASKDROPBOX_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if item.strip()
]
BASE_URL = os.environ.get("TASKDROPBOX_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
TIME_ZONE = os.environ.get("TASKDROPBOX_TIME_ZONE", "Europe/Oslo")
DATA_DIR = Path(os.environ.get("TASKDROPBOX_DATA_DIR", BASE_DIR / "data")).resolve()
PRIVATE_FILES_DIR = DATA_DIR / "files"
CREATOR_PIN_HASH = os.environ.get("TASKDROPBOX_CREATOR_PIN_HASH", "")
MAX_TASK_ATTACHMENTS = env_int("TASKDROPBOX_MAX_TASK_ATTACHMENTS", 10)
MAX_FILE_BYTES = env_int("TASKDROPBOX_MAX_FILE_MIB", 25) * 1024 * 1024
MAX_SUBMISSION_BYTES = env_int("TASKDROPBOX_MAX_SUBMISSION_MIB", 50) * 1024 * 1024
MAX_FILES_PER_SUBMISSION = env_int("TASKDROPBOX_MAX_FILES_PER_SUBMISSION", 10)
MIN_FREE_DISK_BYTES = env_int("TASKDROPBOX_MIN_FREE_DISK_MIB", 1024) * 1024 * 1024
CREATOR_SESSION_SECONDS = env_int("TASKDROPBOX_CREATOR_SESSION_HOURS", 8) * 3600
ADMIN_SESSION_SECONDS = env_int("TASKDROPBOX_ADMIN_SESSION_HOURS", 8) * 3600
CREATOR_PIN_GLOBAL_ATTEMPTS = env_int("TASKDROPBOX_CREATOR_PIN_GLOBAL_ATTEMPTS", 50)
CREATOR_PIN_WINDOW_SECONDS = env_int("TASKDROPBOX_CREATOR_PIN_WINDOW_SECONDS", 300)
CREATOR_PIN_LOCK_SECONDS = env_int("TASKDROPBOX_CREATOR_PIN_LOCK_SECONDS", 300)

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "drops",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "drops.middleware.CorrelationIdMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "drops.middleware.SecurityHeadersMiddleware",
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
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATA_DIR / "db.sqlite3",
        "OPTIONS": {"timeout": 20, "transaction_mode": "IMMEDIATE"},
    }
}

LANGUAGE_CODE = "en"
USE_I18N = True
USE_TZ = True
LOCALE_PATHS = [BASE_DIR / "locale"]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
SOURCE_ARCHIVE = BASE_DIR / "public" / "taskdropbox-source.tar.gz"

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = False  # V1 deliberately runs over HTTP on an isolated LAN.
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = False
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "no-referrer"
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_SUBMISSION_BYTES + 5 * 1024 * 1024

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"redact_capabilities": {"()": "drops.logging_filters.RedactCapabilitiesFilter"}},
    "formatters": {"standard": {"format": "{asctime} {levelname} {name} {message}", "style": "{"}},
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "filters": ["redact_capabilities"],
        }
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "CRITICAL", "propagate": False}
    },
}
