import shutil

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone

from drops.models import Submission, Task


class Command(BaseCommand):
    help = "Show operational status without exposing capability keys or student content."

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
        usage = shutil.disk_usage(settings.DATA_DIR)
        lines = [
            "TaskDropBox status",
            f"Base URL: {settings.BASE_URL}",
            f"Server time: {timezone.localtime().isoformat()}",
            f"Timezone: {settings.TIME_ZONE}",
            f"Data directory: {settings.DATA_DIR}",
            f"Free space MiB: {usage.free // (1024 * 1024)}",
            f"Tasks: {Task.objects.count()}",
            f"Open tasks: {Task.objects.filter(status=Task.Status.OPEN).count()}",
            f"Submissions: {Submission.objects.count()}",
            "Database: OK",
        ]
        self.stdout.write("\n".join(lines))
