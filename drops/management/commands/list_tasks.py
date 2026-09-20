from django.core.management.base import BaseCommand
from django.db.models import Count, Sum

from drops.models import SubmissionFile, Task, TaskAttachment


class Command(BaseCommand):
    help = "List tasks without exposing pupil data or capability keys."

    def handle(self, *args, **options):
        tasks = Task.objects.annotate(submission_count=Count("submissions")).order_by("-created_at")
        if not tasks.exists():
            self.stdout.write("No tasks.")
            return
        for task in tasks:
            task_bytes = TaskAttachment.objects.filter(task=task).aggregate(
                total=Sum("size_bytes")
            )["total"] or 0
            submission_bytes = SubmissionFile.objects.filter(submission__task=task).aggregate(
                total=Sum("size_bytes")
            )["total"] or 0
            self.stdout.write(
                f"{task.id}  {task.status:<6}  submissions={task.submission_count:<4} "
                f"bytes={task_bytes + submission_bytes:<10}  {task.title}"
            )
