import io
import tempfile
from unittest.mock import patch
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from drops.models import Task
from drops.tokens import digest_token, new_admin_token, new_student_token


class ManagementCommandTests(TransactionTestCase):
    def create_task(self, title="Emergency task"):
        return Task.objects.create(
            title=title,
            instructions_text="Instructions",
            student_token_hash=digest_token(new_student_token()),
            admin_token_hash=digest_token(new_admin_token()),
        )

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

    def test_list_tasks_omits_capability_hashes(self):
        task = self.create_task()
        output = io.StringIO()
        call_command("list_tasks", stdout=output)
        rendered = output.getvalue()
        self.assertIn(str(task.id), rendered)
        self.assertIn(task.title, rendered)
        self.assertNotIn(task.student_token_hash, rendered)
        self.assertNotIn(task.admin_token_hash, rendered)

    def test_delete_task_command_requires_exact_confirmation(self):
        task = self.create_task()
        with patch("builtins.input", return_value="no"):
            with self.assertRaisesMessage(CommandError, "Deletion cancelled"):
                call_command("delete_task", str(task.id), stdout=io.StringIO())
        self.assertTrue(Task.objects.filter(pk=task.id).exists())
        with patch("builtins.input", return_value=f"DELETE {task.id}"):
            call_command("delete_task", str(task.id), stdout=io.StringIO())
        self.assertFalse(Task.objects.filter(pk=task.id).exists())

    def test_close_all_requires_confirmation(self):
        self.create_task()
        with patch("builtins.input", return_value="CLOSE ALL TASKS"):
            call_command("close_all", stdout=io.StringIO())
        self.assertFalse(Task.objects.filter(status=Task.Status.OPEN).exists())

    def test_flush_data_removes_tasks_and_private_files(self):
        self.create_task()
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            private_files = data_dir / "files"
            private_files.mkdir()
            (private_files / "orphan").write_bytes(b"private")
            with override_settings(DATA_DIR=data_dir, PRIVATE_FILES_DIR=private_files):
                with patch("builtins.input", return_value="DELETE ALL TASKDROPBOX DATA"):
                    call_command("flush_data", stdout=io.StringIO())
                self.assertTrue(private_files.is_dir())
                self.assertEqual(list(private_files.iterdir()), [])
        self.assertFalse(Task.objects.exists())


class SourceArchiveTests(TestCase):
    def test_installed_source_archive_is_downloadable(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "source.tar.gz"
            archive.write_bytes(b"source archive")
            with override_settings(SOURCE_ARCHIVE=archive):
                response = self.client.get(reverse("source_archive"))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(b"".join(response.streaming_content), b"source archive")
