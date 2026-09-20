from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from drops.models import Task


class Command(BaseCommand):
    help = "Close every open task after explicit confirmation."

    def handle(self, *args, **options):
        count = Task.objects.filter(status=Task.Status.OPEN).count()
        self.stdout.write(f"Open tasks: {count}")
        if not count:
            return
        if input("Type CLOSE ALL TASKS to continue: ") != "CLOSE ALL TASKS":
            raise CommandError("Operation cancelled; no tasks were changed.")
        changed = Task.objects.filter(status=Task.Status.OPEN).update(
            status=Task.Status.CLOSED, closed_at=timezone.now()
        )
        self.stdout.write(self.style.SUCCESS(f"Closed {changed} tasks."))
