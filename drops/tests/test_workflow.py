import io
import tempfile
import zipfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.hashers import make_password
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from drops.models import Submission, Task
from drops.tokens import digest_token, new_admin_token, new_student_token


class WorkflowTests(TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.settings_override = override_settings(
            CREATOR_PIN_HASH=make_password("012345"),
            BASE_URL="http://10.20.0.10",
            DATA_DIR=root,
            PRIVATE_FILES_DIR=root / "files",
            MIN_FREE_DISK_BYTES=0,
        )
        self.settings_override.enable()

    def tearDown(self):
        self.settings_override.disable()
        self.temporary.cleanup()

    def test_same_origin_form_posts_preserve_their_origin(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.headers["Referrer-Policy"], "same-origin")

    def create_task_through_ui(self, **overrides):
        response = self.client.post(reverse("creator_login"), {"pin": "012345"})
        self.assertRedirects(response, reverse("task_create"))
        response = self.client.get(reverse("task_create"))
        payload = {
            "title": "Volcano assignment",
            "instructions_text": "Explain how a volcano forms.",
            "allow_text": "on",
            "allow_files": "on",
            "creation_nonce": response.context["form"].initial["creation_nonce"],
        }
        payload.update(overrides)
        response = self.client.post(reverse("task_create"), payload)
        self.assertEqual(response.status_code, 200)
        task = Task.objects.get()
        student_url = response.context["student_url"]
        admin_url = response.context["admin_url"]
        return task, student_url.rstrip("/").split("/")[-1], admin_url.rstrip("/").split("/")[-1]

    def test_complete_create_submit_review_flow(self):
        task, student_token, admin_token = self.create_task_through_ui()
        self.assertNotIn(student_token, task.student_token_hash)
        self.assertNotIn(admin_token, task.admin_token_hash)

        response = self.client.get(reverse("student_task", args=[student_token]))
        self.assertContains(response, "Volcano assignment")
        idempotency_key = response.context["form"].initial["idempotency_key"]
        response = self.client.post(
            reverse("submit_task", args=[student_token]),
            {
                "student_name": "Anna Hansen",
                "answer_text": "Pressure moves magma upward.",
                "idempotency_key": idempotency_key,
                "files": SimpleUploadedFile("diagram.txt", b"diagram"),
            },
        )
        submission = Submission.objects.get()
        self.assertRedirects(response, reverse("submission_receipt", args=[submission.receipt_id]))
        self.assertFalse(submission.is_late)
        self.assertEqual(submission.files.get().original_name, "diagram.txt")

        response = self.client.get(reverse("admin_exchange", args=[admin_token]))
        self.assertRedirects(response, reverse("manage_task", args=[task.id]))
        response = self.client.get(reverse("manage_task", args=[task.id]))
        self.assertContains(response, "Anna Hansen")
        self.assertContains(response, "Pressure moves magma upward.")

    @override_settings(CREATOR_PIN_GLOBAL_ATTEMPTS=2, CREATOR_PIN_LOCK_SECONDS=300)
    def test_creator_pin_is_globally_throttled(self):
        self.client.post(reverse("creator_login"), {"pin": "999999"})
        self.client.post(reverse("creator_login"), {"pin": "999999"})
        response = Client().post(reverse("creator_login"), {"pin": "012345"})
        self.assertEqual(response.status_code, 429)

    def test_unrelated_browser_cannot_manage_task(self):
        task, _, _ = self.create_task_through_ui()
        response = Client().get(reverse("manage_task", args=[task.id]))
        self.assertEqual(response.status_code, 404)

    def test_admin_grant_is_scoped_to_one_task(self):
        first, _, first_admin = self.create_task_through_ui()
        other_student = new_student_token()
        other_admin = new_admin_token()
        second = Task.objects.create(
            title="Other task",
            instructions_text="Other instructions",
            student_token_hash=digest_token(other_student),
            admin_token_hash=digest_token(other_admin),
        )
        self.client.get(reverse("admin_exchange", args=[first_admin]))
        self.assertEqual(self.client.get(reverse("manage_task", args=[first.id])).status_code, 200)
        self.assertEqual(self.client.get(reverse("manage_task", args=[second.id])).status_code, 404)

    def test_overdue_open_task_accepts_and_marks_late(self):
        task, student_token, _ = self.create_task_through_ui(
            due_at=(timezone.now() - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M")
        )
        response = self.client.post(
            reverse("submit_task", args=[student_token]),
            {
                "student_name": "Late Student",
                "answer_text": "Finished.",
                "idempotency_key": new_student_token(),
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(task.submissions.get().is_late)

    def test_submission_at_exact_due_instant_is_on_time(self):
        due = timezone.now().replace(microsecond=0)
        task, student_token, _ = self.create_task_through_ui(
            due_at=due.strftime("%Y-%m-%dT%H:%M")
        )
        task.refresh_from_db()
        with patch("drops.services.timezone.now", return_value=task.due_at):
            response = self.client.post(
                reverse("submit_task", args=[student_token]),
                {
                    "student_name": "Boundary Student",
                    "answer_text": "Finished exactly on time.",
                    "idempotency_key": new_student_token(),
                },
            )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(task.submissions.get().is_late)

    def test_closed_task_rejects_submission_and_reopen_allows_late(self):
        task, student_token, admin_token = self.create_task_through_ui(
            due_at=(timezone.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
        )
        self.client.get(reverse("admin_exchange", args=[admin_token]))
        self.client.post(reverse("close_task", args=[task.id]))
        response = self.client.post(
            reverse("submit_task", args=[student_token]),
            {
                "student_name": "Student",
                "answer_text": "Answer",
                "idempotency_key": new_student_token(),
            },
        )
        self.assertEqual(response.status_code, 409)
        self.assertFalse(Submission.objects.exists())
        self.client.post(reverse("reopen_task", args=[task.id]))
        response = self.client.post(
            reverse("submit_task", args=[student_token]),
            {
                "student_name": "Student",
                "answer_text": "Answer",
                "idempotency_key": new_student_token(),
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Submission.objects.get().is_late)

    def test_front_page_accepts_student_and_admin_keys(self):
        task, student_token, admin_token = self.create_task_through_ui()
        response = self.client.post(reverse("open_student"), {"student-key": student_token})
        self.assertRedirects(response, reverse("student_task", args=[student_token]))
        response = self.client.post(reverse("open_admin"), {"admin-key": admin_token})
        self.assertRedirects(response, reverse("manage_task", args=[task.id]))

    def test_zip_export_uses_safe_readable_names_and_manifest(self):
        task, student_token, admin_token = self.create_task_through_ui()
        self.client.post(
            reverse("submit_task", args=[student_token]),
            {
                "student_name": "=Anna/../Hansen",
                "answer_text": "Web answer",
                "idempotency_key": new_student_token(),
                "files": SimpleUploadedFile("../notes.txt", b"notes"),
            },
        )
        self.client.get(reverse("admin_exchange", args=[admin_token]))
        response = self.client.get(reverse("export_task", args=[task.id]))
        self.assertEqual(response.status_code, 200)
        payload = b"".join(response.streaming_content)
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            names = archive.namelist()
            self.assertTrue(any(name.endswith("manifest.csv") for name in names))
            self.assertFalse(any("../" in name or name.startswith("/") for name in names))
            manifest_name = next(name for name in names if name.endswith("manifest.csv"))
            manifest = archive.read(manifest_name).decode("utf-8-sig")
            self.assertIn("'=Anna/../Hansen", manifest)
            self.assertTrue(any(name.endswith(" - webgui.txt") for name in names))

    def test_task_deletion_removes_database_rows_and_files(self):
        task, student_token, admin_token = self.create_task_through_ui()
        self.client.post(
            reverse("submit_task", args=[student_token]),
            {
                "student_name": "Student",
                "answer_text": "Answer",
                "idempotency_key": new_student_token(),
                "files": SimpleUploadedFile("work.txt", b"private"),
            },
        )
        stored_path = self.settings_override.options["PRIVATE_FILES_DIR"] / Submission.objects.get().files.get().storage_name
        self.assertTrue(stored_path.exists())
        self.client.get(reverse("admin_exchange", args=[admin_token]))
        response = self.client.post(reverse("delete_task", args=[task.id]))
        self.assertRedirects(response, reverse("home"))
        self.assertFalse(Task.objects.exists())
        self.assertFalse(Submission.objects.exists())
        self.assertFalse(stored_path.exists())

    def test_task_without_files_can_be_deleted(self):
        task, _, admin_token = self.create_task_through_ui()
        self.client.get(reverse("admin_exchange", args=[admin_token]))
        response = self.client.post(reverse("delete_task", args=[task.id]))
        self.assertRedirects(response, reverse("home"))
        self.assertFalse(Task.objects.filter(pk=task.id).exists())

    def test_submission_deletion_preserves_other_submission(self):
        task, student_token, admin_token = self.create_task_through_ui()
        for name in ("First Student", "Second Student"):
            self.client.post(
                reverse("submit_task", args=[student_token]),
                {
                    "student_name": name,
                    "answer_text": "Answer",
                    "idempotency_key": new_student_token(),
                    "files": SimpleUploadedFile(f"{name}.txt", name.encode()),
                },
            )
        first = task.submissions.get(student_name="First Student")
        second = task.submissions.get(student_name="Second Student")
        first_path = self.settings_override.options["PRIVATE_FILES_DIR"] / first.files.get().storage_name
        second_path = self.settings_override.options["PRIVATE_FILES_DIR"] / second.files.get().storage_name
        self.client.get(reverse("admin_exchange", args=[admin_token]))
        response = self.client.post(reverse("delete_submission", args=[task.id, first.id]))
        self.assertRedirects(response, reverse("manage_task", args=[task.id]))
        self.assertFalse(Submission.objects.filter(pk=first.id).exists())
        self.assertTrue(Submission.objects.filter(pk=second.id).exists())
        self.assertFalse(first_path.exists())
        self.assertTrue(second_path.exists())

    def test_submission_file_cannot_be_downloaded_with_other_task_grant(self):
        first, first_student, first_admin = self.create_task_through_ui()
        self.client.post(
            reverse("submit_task", args=[first_student]),
            {
                "student_name": "Student",
                "answer_text": "Answer",
                "idempotency_key": new_student_token(),
                "files": SimpleUploadedFile("private.txt", b"private"),
            },
        )
        file_id = first.submissions.get().files.get().id
        second_admin = new_admin_token()
        second = Task.objects.create(
            title="Other",
            instructions_text="Other",
            student_token_hash=digest_token(new_student_token()),
            admin_token_hash=digest_token(second_admin),
        )
        self.client.get(reverse("admin_exchange", args=[first_admin]))
        self.client.get(reverse("admin_exchange", args=[second_admin]))
        self.assertEqual(
            self.client.get(reverse("submission_file_download", args=[second.id, file_id])).status_code,
            404,
        )

    def test_repeated_submission_nonce_returns_the_original_receipt(self):
        task, student_token, _ = self.create_task_through_ui()
        key = new_student_token()
        payload = {"student_name": "Student", "answer_text": "Answer", "idempotency_key": key}
        first = self.client.post(reverse("submit_task", args=[student_token]), payload)
        second = self.client.post(reverse("submit_task", args=[student_token]), payload)
        self.assertEqual(first.url, second.url)
        self.assertEqual(task.submissions.count(), 1)

    def test_creation_form_cannot_be_reused(self):
        self.client.post(reverse("creator_login"), {"pin": "012345"})
        response = self.client.get(reverse("task_create"))
        payload = {
            "title": "One",
            "instructions_text": "Instructions",
            "allow_text": "on",
            "creation_nonce": response.context["form"].initial["creation_nonce"],
        }
        self.assertEqual(self.client.post(reverse("task_create"), payload).status_code, 200)
        self.assertEqual(self.client.post(reverse("task_create"), payload).status_code, 409)
        self.assertEqual(Task.objects.count(), 1)


class DirectCapabilityTests(TestCase):
    def test_raw_tokens_are_not_stored(self):
        student = new_student_token()
        admin = new_admin_token()
        task = Task.objects.create(
            title="Task",
            instructions_text="Instructions",
            student_token_hash=digest_token(student),
            admin_token_hash=digest_token(admin),
        )
        self.assertNotEqual(task.student_token_hash, student)
        self.assertNotEqual(task.admin_token_hash, admin)
