import uuid

from django.core.management.base import BaseCommand, CommandError

from drops.models import Task
from drops.services import delete_task


class Command(BaseCommand):
    help = "Permanently delete one task after showing a privacy-safe preview."

    def add_arguments(self, parser):
        parser.add_argument("task_id")

    def handle(self, *args, **options):
        try:
            task_id = uuid.UUID(options["task_id"])
            task = Task.objects.get(pk=task_id)
        except (ValueError, Task.DoesNotExist) as error:
            raise CommandError("Task was not found.") from error
        submission_count = task.submissions.count()
        self.stdout.write(f"Task: {task.id}")
        self.stdout.write(f"Title: {task.title}")
        self.stdout.write(f"Status: {task.status}")
        self.stdout.write(f"Submissions: {submission_count}")
        confirmation = input(f"Type DELETE {task.id} to continue: ")
        if confirmation != f"DELETE {task.id}":
            raise CommandError("Deletion cancelled; no data was changed.")
        delete_task(task)
        self.stdout.write(self.style.SUCCESS("Task permanently deleted."))
