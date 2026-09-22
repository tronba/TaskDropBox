"""Isolated review probes; never opens the configured application database.

Run with: python scripts/review_edge_cases.py
Outputs JSON. Known defects are reported as observations, not hidden as passing tests.
This exercises Django and file-backed SQLite, not Nginx/Gunicorn or browser behavior.
"""

import json
import logging
import os
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from pathlib import Path
from threading import Barrier
from unittest.mock import patch


def run(root):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    os.environ.update(
        DJANGO_SETTINGS_MODULE="config.settings",
        TASKDROPBOX_DATA_DIR=str(root),
        TASKDROPBOX_SECRET_KEY="isolated-review-only",
        TASKDROPBOX_BASE_URL="http://127.0.0.1",
        TASKDROPBOX_ALLOWED_HOSTS="127.0.0.1,testserver",
        TASKDROPBOX_MIN_FREE_DISK_MIB="0",
    )
    import django

    django.setup()
    logging.disable(logging.CRITICAL)
    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.core.management import call_command
    from django.db import connections
    from django.test import Client, override_settings

    from drops import services, views
    from drops.auth import CREATOR_SESSION_KEY, pin_fingerprint
    from drops.models import Submission, Task
    from drops.storage import safe_absolute_path
    from drops.tokens import digest_token, new_form_nonce

    call_command("migrate", verbosity=0)
    results = {}

    def task():
        return services.create_task(
            dict(title="Review", instructions_text="<p>Instructions</p>",
                 allow_text=True, allow_files=True), []
        )

    def payload(key=None):
        return dict(student_name="Review pupil", answer_text="Answer",
                    idempotency_key=key or new_form_nonce())

    def parallel(count, workers, action):
        def isolated(index):
            started = time.perf_counter()
            try:
                value = action(index)
                return dict(value=value, seconds=time.perf_counter() - started)
            except Exception as error:
                return dict(error=type(error).__name__, detail=str(error))
            finally:
                connections.close_all()

        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=workers) as pool:
            outcomes = list(pool.map(isolated, range(count)))
        timings = sorted(item["seconds"] for item in outcomes if "seconds" in item)
        return dict(
            requests=count, workers=workers,
            elapsed_seconds=round(time.perf_counter() - started, 3),
            p95_seconds=round(timings[min(len(timings) - 1, int(len(timings) * .95))], 3)
            if timings else None,
            errors=[item for item in outcomes if "error" in item],
            outcomes=outcomes,
        )

    try:
        for count, workers in ((30, 30), (100, 32), (300, 32)):
            current, student, _ = task()

            def submit(index):
                data = payload()
                data["files"] = SimpleUploadedFile("answer.txt", b"x" * 65536)
                return Client().post(f"/d/{student}/submit/", data).status_code

            result = parallel(count, workers, submit)
            result["status_counts"] = {
                str(status): sum(item.get("value") == status for item in result["outcomes"])
                for status in {item.get("value") for item in result["outcomes"]}
            }
            del result["outcomes"]
            result["stored_submissions"] = current.submissions.count()
            results[f"submission_burst_{count}"] = result

        current, student, _ = task()
        key = new_form_nonce()
        duplicate = parallel(
            30, 30,
            lambda index: Client().post(f"/d/{student}/submit/", payload(key)).get("Location"),
        )
        duplicate["distinct_receipts"] = len({item.get("value") for item in duplicate.pop("outcomes")})
        duplicate["stored_submissions"] = current.submissions.count()
        results["simultaneous_duplicate_submission"] = duplicate

        current.status = Task.Status.CLOSED
        current.save(update_fields=["status"])
        results["retry_after_close"] = dict(
            expected_status=302,
            actual_status=Client().post(f"/d/{student}/submit/", payload(key)).status_code,
        )
        current.status = Task.Status.OPEN
        current.save(update_fields=["status"])
        with patch("drops.services.ensure_space", return_value=False):
            results["retry_when_disk_reserve_reached"] = dict(
                expected_status=302,
                actual_status=Client().post(f"/d/{student}/submit/", payload(key)).status_code,
            )

        current, _, _ = task()
        original_stage = services.stage_deletions
        uploaded_paths = []

        def concurrent_upload():
            try:
                accepted = services.create_submission(
                    current, payload(), [SimpleUploadedFile("private.txt", b"private pupil data")]
                )
                uploaded_paths.append(safe_absolute_path(accepted.files.get().storage_name))
                return "accepted"
            except services.TaskClosedError:
                return "task deleted; upload rejected"
            finally:
                connections.close_all()

        # Use another connection: a same-thread callback would participate in the
        # deletion transaction and would not model another pupil's request.
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = []

            def upload_between_enumeration_and_deletion(names):
                future = pool.submit(concurrent_upload)
                pending.append(future)
                try:
                    future.result(timeout=2)
                except TimeoutError:
                    # Correctly serialized uploads wait for deletion to commit.
                    pass
                return original_stage(names)

            with patch("drops.services.stage_deletions", side_effect=upload_between_enumeration_and_deletion):
                services.delete_task(current)
            upload_outcome = pending[0].result(timeout=25)
        results["submission_during_task_deletion"] = dict(
            expected_orphan_files=0,
            actual_orphan_files=sum(path.exists() for path in uploaded_paths),
            upload_outcome=upload_outcome,
        )

        current, _, _ = task()
        before_files = set((root / "files").rglob("*"))
        with patch("drops.services.SubmissionFile.objects.create", side_effect=RuntimeError("injected failure")):
            try:
                services.create_submission(current, payload(), [SimpleUploadedFile("work.txt", b"work")])
            except RuntimeError:
                pass
        results["database_failure_after_file_move"] = dict(
            stored_submissions=current.submissions.count(),
            remaining_new_files=[str(path.relative_to(root)) for path in set((root / "files").rglob("*")) - before_files if path.is_file()],
        )

        current, student, _ = task()
        endpoint = f"/d/{student}/submit/"
        validation = {}

        def rejected(label, data, expected=400, client=None):
            validation[label] = dict(
                expected_status=expected,
                actual_status=(client or Client()).post(endpoint, data).status_code,
            )

        rejected("missing_csrf", payload(), 403, Client(enforce_csrf_checks=True))
        empty = payload()
        empty["answer_text"] = ""
        rejected("empty_answer", empty)
        with override_settings(MAX_FILE_BYTES=4, MAX_SUBMISSION_BYTES=6, MAX_FILES_PER_SUBMISSION=2):
            for label, contents in (
                ("file_too_large", [b"12345"]),
                ("combined_files_too_large", [b"1234", b"1234"]),
                ("too_many_files", [b"1", b"2", b"3"]),
            ):
                data = payload()
                data["files"] = [SimpleUploadedFile(f"{index}.txt", content) for index, content in enumerate(contents)]
                rejected(label, data)
        rejected("idempotency_key_from_other_task", payload(key), 404)
        validation["stored_submissions"] = current.submissions.count()
        results["input_validation"] = validation

        nonce = new_form_nonce()
        owner = Client()
        session = owner.session
        session[CREATOR_SESSION_KEY] = pin_fingerprint()
        session[views.CREATION_NONCES_SESSION_KEY] = [digest_token(nonce)]
        session.save()
        original_create = views.create_task
        gate = Barrier(2, timeout=10)

        def simultaneous_create(*args, **kwargs):
            gate.wait()
            return original_create(*args, **kwargs)

        def create(index):
            client = Client()
            client.cookies = owner.cookies.copy()
            return client.post("/create/", dict(
                title="Concurrent creation", instructions_text="Instructions",
                allow_text="on", creation_nonce=nonce,
            )).status_code

        before = Task.objects.count()
        with patch("drops.views.create_task", side_effect=simultaneous_create):
            creation = parallel(2, 2, create)
        creation["created_tasks"] = Task.objects.count() - before
        creation["expected_created_tasks"] = 1
        results["simultaneous_duplicate_task_creation"] = creation
        results["database_integrity"] = {}
        with connections["default"].cursor() as cursor:
            cursor.execute("PRAGMA integrity_check")
            results["database_integrity"]["integrity_check"] = cursor.fetchall()
            cursor.execute("PRAGMA foreign_key_check")
            results["database_integrity"]["foreign_key_check"] = cursor.fetchall()
        results["total_submissions"] = Submission.objects.count()
        return results
    finally:
        connections.close_all()


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="taskdropbox-review-") as directory:
        print(json.dumps(run(Path(directory)), indent=2))
