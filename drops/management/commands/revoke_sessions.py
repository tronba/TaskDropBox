from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Invalidate every creator and teacher browser session."

    def handle(self, *args, **options):
        count, _ = Session.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"Revoked {count} browser sessions."))
