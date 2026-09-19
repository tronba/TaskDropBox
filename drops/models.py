import uuid

from django.core.validators import MaxLengthValidator
from django.db import models


class Task(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    instructions_text = models.TextField(validators=[MaxLengthValidator(20_000)])
    student_token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    admin_token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    allow_text = models.BooleanField(default=True)
    allow_files = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    due_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Task {self.id}"


class StoredFile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_name = models.CharField(max_length=255)
    storage_name = models.CharField(max_length=255, unique=True)
    size_bytes = models.PositiveBigIntegerField()
    content_type_claimed = models.CharField(max_length=255, blank=True)
    sha256 = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class TaskAttachment(StoredFile):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="attachments")


class Submission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="submissions")
    receipt_id = models.CharField(max_length=64, unique=True, db_index=True)
    idempotency_key_hash = models.CharField(max_length=64, unique=True, db_index=True)
    student_name = models.CharField(max_length=150)
    answer_text = models.TextField(blank=True, validators=[MaxLengthValidator(100_000)])
    submitted_at = models.DateTimeField()
    is_late = models.BooleanField(default=False)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"Submission {self.id} for task {self.task_id}"


class SubmissionFile(StoredFile):
    submission = models.ForeignKey(
        Submission, on_delete=models.CASCADE, related_name="files"
    )


class RateLimitBucket(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    window_started_at = models.DateTimeField()
    failures = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
