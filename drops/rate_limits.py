from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import RateLimitBucket

CREATOR_PIN_BUCKET = "creator-pin-global"


def creator_pin_is_allowed():
    now = timezone.now()
    bucket = RateLimitBucket.objects.filter(pk=CREATOR_PIN_BUCKET).first()
    return not bucket or not bucket.locked_until or bucket.locked_until <= now


def record_creator_pin_failure():
    now = timezone.now()
    window = timedelta(seconds=settings.CREATOR_PIN_WINDOW_SECONDS)
    lock = timedelta(seconds=settings.CREATOR_PIN_LOCK_SECONDS)
    with transaction.atomic():
        bucket, _ = RateLimitBucket.objects.select_for_update().get_or_create(
            pk=CREATOR_PIN_BUCKET,
            defaults={"window_started_at": now},
        )
        if now - bucket.window_started_at >= window:
            bucket.window_started_at = now
            bucket.failures = 0
            bucket.locked_until = None
        bucket.failures += 1
        if bucket.failures >= settings.CREATOR_PIN_GLOBAL_ATTEMPTS:
            bucket.locked_until = now + lock
        bucket.save(update_fields=["window_started_at", "failures", "locked_until"])


def reset_creator_pin_failures():
    RateLimitBucket.objects.filter(pk=CREATOR_PIN_BUCKET).delete()
