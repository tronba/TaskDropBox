import logging

from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone

from .models import Submission, SubmissionFile, Task, TaskAttachment
from .storage import (
    commit_upload,
    discard_prepared,
    ensure_space,
    prepare_upload,
    purge_trash,
    remove_storage_name,
    restore_staged,
    stage_deletions,
    UploadTooLargeError,
)
from .tokens import digest_token, new_admin_token, new_receipt_id, new_student_token

logger = logging.getLogger(__name__)


def create_task(cleaned_data, uploaded_files):
    student_token = new_student_token()
    admin_token = new_admin_token()
    prepared = []
    committed = []
    try:
        projected = sum(item.size for item in uploaded_files)
        if not ensure_space(projected):
            raise InsufficientStorageError
        for item in uploaded_files:
            prepared.append(prepare_upload(item, settings.MAX_FILE_BYTES))
        if sum(item.size_bytes for item in prepared) > settings.MAX_SUBMISSION_BYTES:
            raise UploadTooLargeError
        if not ensure_space(0):
            raise InsufficientStorageError
        with transaction.atomic():
            task = Task.objects.create(
                title=cleaned_data["title"].strip(),
                instructions_text=cleaned_data["instructions_text"].strip(),
                due_at=cleaned_data.get("due_at"),
                allow_text=cleaned_data["allow_text"],
                allow_files=cleaned_data["allow_files"],
                student_token_hash=digest_token(student_token),
                admin_token_hash=digest_token(admin_token),
            )
            for item in prepared:
                storage_name = commit_upload(item, "task_attachments")
                committed.append(storage_name)
                TaskAttachment.objects.create(
                    task=task,
                    original_name=item.original_name,
                    storage_name=storage_name,
                    size_bytes=item.size_bytes,
                    content_type_claimed=item.content_type,
                    sha256=item.sha256,
                )
        logger.info("task_created task=%s", task.id)
        return task, student_token, admin_token
    except Exception:
        for storage_name in committed:
            remove_storage_name(storage_name)
        raise
    finally:
        discard_prepared(prepared)


def create_submission(task, cleaned_data, uploaded_files):
    prepared = []
    committed = []
    try:
        projected = sum(item.size for item in uploaded_files)
        if not ensure_space(projected):
            raise InsufficientStorageError
        for item in uploaded_files:
            prepared.append(prepare_upload(item, settings.MAX_FILE_BYTES))
        if sum(item.size_bytes for item in prepared) > settings.MAX_SUBMISSION_BYTES:
            raise UploadTooLargeError
        if not ensure_space(0):
            raise InsufficientStorageError
        now = timezone.now()
        with transaction.atomic():
            locked_task = Task.objects.select_for_update().get(pk=task.pk)
            key_hash = digest_token(cleaned_data["idempotency_key"])
            existing = Submission.objects.filter(idempotency_key_hash=key_hash).first()
            if existing:
                if existing.task_id == locked_task.id:
                    return existing
                raise InvalidIdempotencyKeyError
            if locked_task.status != Task.Status.OPEN:
                raise TaskClosedError
            submission = Submission.objects.create(
                task=locked_task,
                receipt_id=new_receipt_id(),
                idempotency_key_hash=key_hash,
                student_name=cleaned_data["student_name"],
                answer_text=cleaned_data.get("answer_text", ""),
                submitted_at=now,
                is_late=bool(locked_task.due_at and now > locked_task.due_at),
            )
            for item in prepared:
                storage_name = commit_upload(item, "submission_files")
                committed.append(storage_name)
                SubmissionFile.objects.create(
                    submission=submission,
                    original_name=item.original_name,
                    storage_name=storage_name,
                    size_bytes=item.size_bytes,
                    content_type_claimed=item.content_type,
                    sha256=item.sha256,
                )
        logger.info(
            "submission_accepted task=%s submission=%s late=%s",
            task.id,
            submission.id,
            submission.is_late,
        )
        return submission
    except Exception:
        for storage_name in committed:
            remove_storage_name(storage_name)
        raise
    finally:
        discard_prepared(prepared)


class TaskClosedError(Exception):
    pass


class InsufficientStorageError(Exception):
    pass


class InvalidIdempotencyKeyError(Exception):
    pass


def delete_submission(submission):
    names = list(submission.files.values_list("storage_name", flat=True))
    trash, staged = stage_deletions(names)
    try:
        with transaction.atomic():
            submission_id = submission.id
            task_id = submission.task_id
            submission.delete()
    except Exception:
        restore_staged(staged)
        purge_trash(trash, ignore_errors=True)
        raise
    try:
        purge_trash(trash)
    except Exception:
        logger.critical("submission_file_cleanup_failed trash=%s", trash)
        raise
    checkpoint_after_deletion()
    logger.info("submission_deleted task=%s submission=%s", task_id, submission_id)


def delete_task(task):
    names = list(task.attachments.values_list("storage_name", flat=True))
    names.extend(
        SubmissionFile.objects.filter(submission__task=task).values_list("storage_name", flat=True)
    )
    trash, staged = stage_deletions(names)
    try:
        with transaction.atomic():
            task_id = task.id
            task.delete()
    except Exception:
        restore_staged(staged)
        purge_trash(trash, ignore_errors=True)
        raise
    try:
        purge_trash(trash)
    except Exception:
        logger.critical("task_file_cleanup_failed trash=%s", trash)
        raise
    checkpoint_after_deletion()
    logger.info("task_deleted task=%s", task_id)


def checkpoint_after_deletion():
    if connection.vendor != "sqlite":
        return
    try:
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            result = cursor.fetchone()
        if result and result[0]:
            logger.warning("sqlite_wal_checkpoint_busy result=%s", result)
    except Exception:
        logger.exception("sqlite_wal_checkpoint_failed")
