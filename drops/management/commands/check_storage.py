import hashlib
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from drops.models import SubmissionFile, TaskAttachment
from drops.storage import safe_absolute_path


class Command(BaseCommand):
    help = "Report missing and orphaned private files without changing anything."

    def add_arguments(self, parser):
        parser.add_argument("--checksums", action="store_true", help="Also verify SHA-256 checksums.")

    def handle(self, *args, **options):
        records = list(TaskAttachment.objects.all()) + list(SubmissionFile.objects.all())
        expected = {item.storage_name for item in records}
        missing = []
        mismatched = []
        for item in records:
            path = safe_absolute_path(item.storage_name)
            if not path.is_file():
                missing.append(item.storage_name)
            elif options["checksums"] and file_sha256(path) != item.sha256:
                mismatched.append(item.storage_name)

        actual = set()
        if settings.PRIVATE_FILES_DIR.exists():
            for category in ("task_attachments", "submission_files"):
                directory = settings.PRIVATE_FILES_DIR / category
                if directory.exists():
                    actual.update(path.relative_to(settings.PRIVATE_FILES_DIR).as_posix() for path in directory.iterdir() if path.is_file())
        orphaned = sorted(actual - expected)
        temporary_leftovers = []
        for internal_name in (".tmp", ".trash"):
            internal = settings.PRIVATE_FILES_DIR / internal_name
            if internal.exists():
                temporary_leftovers.extend(
                    path.relative_to(settings.PRIVATE_FILES_DIR).as_posix()
                    for path in internal.rglob("*")
                    if path.is_file()
                )

        self.stdout.write(f"Records checked: {len(records)}")
        self.stdout.write(f"Missing files: {len(missing)}")
        self.stdout.write(f"Orphaned files: {len(orphaned)}")
        self.stdout.write(f"Temporary/trash files: {len(temporary_leftovers)}")
        self.stdout.write(f"Checksum mismatches: {len(mismatched)}")
        for label, values in (
            ("MISSING", missing),
            ("ORPHAN", orphaned),
            ("TEMPORARY", temporary_leftovers),
            ("CHECKSUM", mismatched),
        ):
            for value in values:
                self.stdout.write(f"{label}: {value}")
        if missing or orphaned or temporary_leftovers or mismatched:
            raise SystemExit(1)


def file_sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
