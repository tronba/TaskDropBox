from urllib.parse import urlparse

from django.conf import settings
from django.core.checks import Error, Warning, register


@register()
def taskdropbox_settings_check(app_configs, **kwargs):
    issues = []
    parsed = urlparse(settings.BASE_URL)
    try:
        valid_port = parsed.port in (None, 80, 443)
    except ValueError:
        valid_port = False
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or not valid_port
        or parsed.path not in {"", "/"}
    ):
        issues.append(Error("TASKDROPBOX_BASE_URL must be an HTTP(S) origin without a path.", id="taskdropbox.E001"))
    if settings.CREATOR_PIN_HASH and not settings.CREATOR_PIN_HASH.startswith(("argon2$", "pbkdf2_")):
        issues.append(Error("TASKDROPBOX_CREATOR_PIN_HASH is not a supported Django password hash.", id="taskdropbox.E002"))
    if not settings.CREATOR_PIN_HASH:
        issues.append(Warning("No creator PIN hash is configured; task creation is disabled.", id="taskdropbox.W001"))
    if not settings.DEBUG and settings.SECRET_KEY == "development-only-not-for-production":
        issues.append(Error("TASKDROPBOX_SECRET_KEY must be configured in production.", id="taskdropbox.E005"))
    if parsed.hostname and parsed.hostname not in settings.ALLOWED_HOSTS:
        issues.append(Error("The TASKDROPBOX_BASE_URL host must appear in TASKDROPBOX_ALLOWED_HOSTS.", id="taskdropbox.E006"))
    if settings.MAX_FILE_BYTES <= 0 or settings.MAX_SUBMISSION_BYTES < settings.MAX_FILE_BYTES:
        issues.append(Error("Upload size settings are inconsistent.", id="taskdropbox.E003"))
    if settings.MIN_FREE_DISK_BYTES < 0:
        issues.append(Error("Disk reserve cannot be negative.", id="taskdropbox.E004"))
    return issues
