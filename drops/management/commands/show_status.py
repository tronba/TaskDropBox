import shutil
import socket
from importlib.metadata import PackageNotFoundError, version

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
        try:
            application_version = version("taskdropbox")
        except PackageNotFoundError:
            application_version = "development"
        try:
            detected_ips = sorted(
                {
                    item[4][0]
                    for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
                    if not item[4][0].startswith("127.")
                }
            )
        except OSError:
            detected_ips = []
        lines = [
            "TaskDropBox status",
            f"Version: {application_version}",
            f"Base URL: {settings.BASE_URL}",
            f"Detected IPv4 addresses: {', '.join(detected_ips) or 'none'}",
            f"Server time: {timezone.localtime().isoformat()}",
            f"Timezone: {settings.TIME_ZONE}",
            f"Default web language: {settings.LANGUAGE_CODE}",
            f"Data directory: {settings.DATA_DIR}",
            f"Free space MiB: {usage.free // (1024 * 1024)}",
            f"Tasks: {Task.objects.count()}",
            f"Open tasks: {Task.objects.filter(status=Task.Status.OPEN).count()}",
            f"Submissions: {Submission.objects.count()}",
            "Database: OK",
        ]
        self.stdout.write("\n".join(lines))
