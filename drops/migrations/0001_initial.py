import uuid

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="RateLimitBucket",
            fields=[
                ("key", models.CharField(max_length=64, primary_key=True, serialize=False)),
                ("window_started_at", models.DateTimeField()),
                ("failures", models.PositiveIntegerField(default=0)),
                ("locked_until", models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name="Task",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=200)),
                ("instructions_text", models.TextField(validators=[django.core.validators.MaxLengthValidator(20000)])),
                ("student_token_hash", models.CharField(db_index=True, max_length=64, unique=True)),
                ("admin_token_hash", models.CharField(db_index=True, max_length=64, unique=True)),
                ("status", models.CharField(choices=[("open", "Open"), ("closed", "Closed")], default="open", max_length=10)),
                ("allow_text", models.BooleanField(default=True)),
                ("allow_files", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("due_at", models.DateTimeField(blank=True, null=True)),
                ("closed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="Submission",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("receipt_id", models.CharField(db_index=True, max_length=64, unique=True)),
                ("idempotency_key_hash", models.CharField(db_index=True, max_length=64, unique=True)),
                ("student_name", models.CharField(max_length=150)),
                ("answer_text", models.TextField(blank=True, validators=[django.core.validators.MaxLengthValidator(100000)])),
                ("submitted_at", models.DateTimeField()),
                ("is_late", models.BooleanField(default=False)),
                ("task", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="submissions", to="drops.task")),
            ],
            options={"ordering": ["-submitted_at"]},
        ),
        migrations.CreateModel(
            name="TaskAttachment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("original_name", models.CharField(max_length=255)),
                ("storage_name", models.CharField(max_length=255, unique=True)),
                ("size_bytes", models.PositiveBigIntegerField()),
                ("content_type_claimed", models.CharField(blank=True, max_length=255)),
                ("sha256", models.CharField(max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("task", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attachments", to="drops.task")),
            ],
        ),
        migrations.CreateModel(
            name="SubmissionFile",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("original_name", models.CharField(max_length=255)),
                ("storage_name", models.CharField(max_length=255, unique=True)),
                ("size_bytes", models.PositiveBigIntegerField()),
                ("content_type_claimed", models.CharField(blank=True, max_length=255)),
                ("sha256", models.CharField(max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("submission", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="files", to="drops.submission")),
            ],
        ),
    ]
