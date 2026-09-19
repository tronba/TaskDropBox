import hashlib

from django.conf import settings
from django.contrib.auth.hashers import check_password

CREATOR_SESSION_KEY = "creator_auth_fingerprint"
ADMIN_GRANTS_KEY = "task_admin_grants"


def pin_fingerprint():
    return hashlib.sha256(settings.CREATOR_PIN_HASH.encode("utf-8")).hexdigest()


def verify_creator_pin(pin):
    return bool(settings.CREATOR_PIN_HASH) and check_password(pin, settings.CREATOR_PIN_HASH)


def authorize_creator(request):
    request.session.cycle_key()
    request.session[CREATOR_SESSION_KEY] = pin_fingerprint()
    request.session.set_expiry(settings.CREATOR_SESSION_SECONDS)


def creator_is_authorized(request):
    return request.session.get(CREATOR_SESSION_KEY) == pin_fingerprint()


def grant_task_admin(request, task_id):
    request.session.cycle_key()
    grants = set(request.session.get(ADMIN_GRANTS_KEY, []))
    grants.add(str(task_id))
    request.session[ADMIN_GRANTS_KEY] = sorted(grants)
    request.session.set_expiry(settings.ADMIN_SESSION_SECONDS)


def has_task_admin(request, task_id):
    return str(task_id) in request.session.get(ADMIN_GRANTS_KEY, [])
