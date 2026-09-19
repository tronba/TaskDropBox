import hashlib
import secrets
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings


def digest_token(raw_token):
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def student_code_words():
    wordlist_path = Path(__file__).with_name("eff_large_wordlist.txt")
    words = []
    for line in wordlist_path.read_text(encoding="utf-8").splitlines():
        _, separator, word = line.partition("\t")
        if separator and word.isascii() and word.isalpha() and word.islower():
            words.append(word)
    if len(words) < 7_700:
        raise RuntimeError("The bundled student-code word list is missing or invalid.")
    return tuple(words)


def new_student_token():
    return "-".join(secrets.choice(student_code_words()) for _ in range(3))


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
