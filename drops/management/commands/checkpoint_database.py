from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Checkpoint and truncate the SQLite write-ahead log."

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            result = cursor.fetchone()
        self.stdout.write(f"WAL checkpoint result: {result}")
