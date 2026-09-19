from django.db import connection
from django.test import TestCase


class SQLiteConfigurationTests(TestCase):
    def test_required_sqlite_pragmas_are_enabled(self):
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA secure_delete")
            self.assertEqual(cursor.fetchone()[0], 1)
            cursor.execute("PRAGMA foreign_keys")
            self.assertEqual(cursor.fetchone()[0], 1)
            cursor.execute("PRAGMA busy_timeout")
            self.assertGreaterEqual(cursor.fetchone()[0], 20_000)
