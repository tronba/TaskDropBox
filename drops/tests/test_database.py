from unittest.mock import Mock, patch

from django.db import connection
from django.test import TestCase

from drops.services import checkpoint_after_deletion


class SQLiteConfigurationTests(TestCase):
    def test_required_sqlite_pragmas_are_enabled(self):
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA secure_delete")
            self.assertEqual(cursor.fetchone()[0], 1)
            cursor.execute("PRAGMA foreign_keys")
            self.assertEqual(cursor.fetchone()[0], 1)
            cursor.execute("PRAGMA busy_timeout")
            self.assertGreaterEqual(cursor.fetchone()[0], 20_000)

    def test_deletion_checkpoint_is_deferred_inside_a_transaction(self):
        database = Mock(vendor="sqlite", in_atomic_block=True)
        with (
            patch("drops.services.connection", database),
            patch("drops.services.transaction.on_commit") as on_commit,
        ):
            checkpoint_after_deletion()
        database.cursor.assert_not_called()
        on_commit.assert_called_once_with(checkpoint_after_deletion)
