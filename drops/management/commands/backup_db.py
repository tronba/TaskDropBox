import sqlite3
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = "Create a transactionally consistent online SQLite backup."

    def add_arguments(self, parser):
        parser.add_argument("output", help="New backup database path; it must not already exist.")

    def handle(self, *args, **options):
        output = Path(options["output"]).expanduser().resolve()
        source = Path(settings.DATABASES["default"]["NAME"]).resolve()
        if output == source:
            raise CommandError("Backup destination cannot be the live database.")
        if output.exists():
            raise CommandError("Backup destination already exists.")
        output.parent.mkdir(parents=True, exist_ok=True)
        connection.ensure_connection()
        try:
            with sqlite3.connect(output) as destination:
                connection.connection.backup(destination)
        except Exception:
            output.unlink(missing_ok=True)
            raise
        self.stdout.write(self.style.SUCCESS(f"Database backup created: {output}"))

