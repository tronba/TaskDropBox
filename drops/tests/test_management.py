import io
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse


class ManagementCommandTests(TransactionTestCase):
    def test_backup_db_creates_consistent_database(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "backup.sqlite3"
            call_command("backup_db", str(output), stdout=io.StringIO())
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 0)

    def test_empty_storage_check_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            with override_settings(PRIVATE_FILES_DIR=Path(directory) / "files"):
                output = io.StringIO()
                call_command("check_storage", stdout=output)
                self.assertIn("Missing files: 0", output.getvalue())

    def test_storage_check_reports_trash_remnants(self):
        with tempfile.TemporaryDirectory() as directory:
            private_files = Path(directory) / "files"
            leftover = private_files / ".trash" / "operation" / "submission_files" / "file"
            leftover.parent.mkdir(parents=True)
            leftover.write_bytes(b"private")
            with override_settings(PRIVATE_FILES_DIR=private_files):
                output = io.StringIO()
                with self.assertRaises(SystemExit):
                    call_command("check_storage", stdout=output)
                self.assertIn("Temporary/trash files: 1", output.getvalue())


class SourceArchiveTests(TestCase):
    def test_installed_source_archive_is_downloadable(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "source.tar.gz"
            archive.write_bytes(b"source archive")
            with override_settings(SOURCE_ARCHIVE=archive):
                response = self.client.get(reverse("source_archive"))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(b"".join(response.streaming_content), b"source archive")
