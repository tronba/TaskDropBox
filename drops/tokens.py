import hashlib
import secrets
from urllib.parse import urlparse

from django.conf import settings


def digest_token(raw_token):
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def new_student_token():
    return secrets.token_urlsafe(16)


def new_admin_token():
    return secrets.token_urlsafe(32)


def new_receipt_id():
    return secrets.token_urlsafe(24)


def new_form_nonce():
    return secrets.token_urlsafe(24)


def extract_key(value, expected_prefix):
    """Accept a raw key or a URL hosted at the configured TaskDropBox origin."""
    value = value.strip()
    if not value or len(value) > 1024:
        return None
    if "://" not in value:
        return value if "/" not in value and "?" not in value and "#" not in value else None

    supplied = urlparse(value)
    base = urlparse(settings.BASE_URL)
    if (supplied.scheme, supplied.netloc) != (base.scheme, base.netloc):
        return None
    parts = [part for part in supplied.path.split("/") if part]
    if len(parts) != 2 or parts[0] != expected_prefix or supplied.query or supplied.fragment:
        return None
    return parts[1]
