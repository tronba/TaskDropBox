import csv
import errno
import io
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from drops.exports import build_task_export
from drops.models import Submission, Task
from drops.services import (
    InsufficientStorageError,
    TaskClosedError,
    create_submission,
    create_task,
    delete_task,
)
from drops.storage import prepare_upload, safe_absolute_path
from drops.tokens import digest_token, new_form_nonce


class EdgeCaseTests(TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        override = override_settings(
            DATA_DIR=self.root, PRIVATE_FILES_DIR=self.root / "files", MIN_FREE_DISK_BYTES=0,
        )
        override.enable()
        self.addCleanup(override.disable)
        self.task, _, _ = create_task({
            "title": "Task", "instructions_text": "<p>Instructions</p>",
            "allow_text": True, "allow_files": True,
        }, [])

    def payload(self):
        return {"student_name": "Student", "answer_text": "<p>Work</p>",
                "idempotency_key": new_form_nonce()}

    def test_submission_retry_does_not_prepare_files_or_require_space(self):
        data = self.payload()
        original = create_submission(self.task, data, [])
        with (
            patch("drops.services.ensure_space", side_effect=AssertionError("checked space")),
            patch("drops.services.prepare_upload", side_effect=AssertionError("copied upload")),
        ):
            retry = create_submission(self.task, data, [SimpleUploadedFile("work.txt", b"work")])
        self.assertEqual(retry.pk, original.pk)

    def test_submission_to_task_deleted_during_upload_cleans_temporary_files(self):
        stale_task = Task.objects.get(pk=self.task.pk)

        def prepare_and_delete(*args, **kwargs):
            prepared = prepare_upload(*args, **kwargs)
            delete_task(self.task)
            return prepared

        with patch("drops.services.prepare_upload", side_effect=prepare_and_delete):
            with self.assertRaises(TaskClosedError):
                create_submission(stale_task, self.payload(), [SimpleUploadedFile("work.txt", b"work")])
        self.assertFalse(Submission.objects.exists())
        self.assertFalse(any(path.is_file() for path in (self.root / "files").rglob("*")))

    def test_failed_task_deletion_restores_files_and_database_rows(self):
        submission = create_submission(
            self.task, self.payload(), [SimpleUploadedFile("work.txt", b"private work")]
        )
        path = safe_absolute_path(submission.files.get().storage_name)
        with patch.object(self.task, "delete", side_effect=RuntimeError("injected failure")):
            with self.assertRaises(RuntimeError):
                delete_task(self.task)
        self.assertTrue(Submission.objects.filter(pk=submission.pk).exists())
        self.assertEqual(path.read_bytes(), b"private work")

    def test_export_preserves_all_answers_across_batch_boundary(self):
        Submission.objects.bulk_create([
            Submission(
                task=self.task, receipt_id=new_form_nonce(),
                idempotency_key_hash=digest_token(new_form_nonce()),
                student_name=f"Pupil {index}", answer_text=f"<p>Answer {index}</p>",
                submitted_at=timezone.now(),
            )
            for index in range(51)
        ])
        spool, _ = build_task_export(self.task)
        with spool, zipfile.ZipFile(spool) as archive:
            names = archive.namelist()
            self.assertEqual(len(names), 103)
            manifest_name = next(name for name in names if name.endswith("manifest.csv"))
            manifest = archive.read(manifest_name)
            self.assertTrue(manifest.startswith(b"\xef\xbb\xbf"))
            rows = list(csv.DictReader(io.StringIO(manifest.decode("utf-8-sig"))))
            self.assertEqual(len(rows), 102)
            self.assertEqual({row["student_name"] for row in rows}, {f"Pupil {i}" for i in range(51)})
            for name in names:
                if name.endswith("webgui.txt"):
                    self.assertTrue(archive.read(name).startswith(b"Answer "))

    def test_export_rejects_low_space_before_creating_output(self):
        with (
            patch("drops.exports.ensure_space", return_value=False),
            patch("drops.exports.tempfile.TemporaryFile") as temporary,
        ):
            with self.assertRaises(InsufficientStorageError):
                build_task_export(self.task)
        temporary.assert_not_called()

    def test_export_closes_partial_output_on_error(self):
        spool = io.BytesIO()
        with (
            patch("drops.exports.tempfile.TemporaryFile", return_value=spool),
            patch("drops.exports._write_task_export", side_effect=OSError(errno.ENOSPC, "full")),
        ):
            with self.assertRaises(InsufficientStorageError):
                build_task_export(self.task)
        self.assertTrue(spool.closed)
