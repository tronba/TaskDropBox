import shutil

from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand, CommandError

from drops.models import RateLimitBucket, Submission, Task
from drops.services import delete_task


class Command(BaseCommand):
    help = "Permanently erase all live TaskDropBox data after explicit confirmation."

    def handle(self, *args, **options):
        task_count = Task.objects.count()
        submission_count = Submission.objects.count()
        self.stdout.write(f"Tasks: {task_count}")
        self.stdout.write(f"Submissions: {submission_count}")
        self.stdout.write(f"Private files: {settings.PRIVATE_FILES_DIR}")
        self.stdout.write("Configuration and the installed application will be preserved.")
        if input("Type DELETE ALL TASKDROPBOX DATA to continue: ") != "DELETE ALL TASKDROPBOX DATA":
            raise CommandError("Flush cancelled; no data was changed.")

        expected = (settings.DATA_DIR.resolve() / "files").resolve()
        private_root = settings.PRIVATE_FILES_DIR.resolve()
        if private_root != expected:
            raise CommandError("Private storage path failed its safety check.")

        for task in list(Task.objects.all()):
            delete_task(task)
        Session.objects.all().delete()
        RateLimitBucket.objects.all().delete()
        if private_root.exists():
            shutil.rmtree(private_root)
        private_root.mkdir(parents=True, mode=0o750)
        self.stdout.write(self.style.SUCCESS("All live TaskDropBox data was permanently erased."))
