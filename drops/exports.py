import csv
import io
import re
import tempfile
import zipfile
from pathlib import PurePosixPath

from django.utils import timezone
from django.utils.text import slugify

from .storage import safe_absolute_path


def safe_component(value, fallback, limit=100):
    value = re.sub(r"[\\/\x00-\x1f\x7f]+", "-", str(value)).strip(" .")
    value = re.sub(r"\s+", " ", value)
    return (value or fallback)[:limit]


def unique_name(candidate, used):
    path = PurePosixPath(candidate)
    result = candidate
    sequence = 2
    while result.casefold() in used:
        suffix = path.suffix
        stem = path.name[: -len(suffix)] if suffix else path.name
        result = f"{stem} ({sequence}){suffix}"
        sequence += 1
    used.add(result.casefold())
    return result


def csv_safe(value):
    text = str(value)
    return "'" + text if text.startswith(("=", "+", "-", "@")) else text


def build_task_export(task):
    spool = tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b")
    date = timezone.localtime(task.created_at).strftime("%Y-%m-%d")
    root = f"{(slugify(task.title) or 'task')[:80]}_{date}"
    rows = []
    with zipfile.ZipFile(spool, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
        submissions = task.submissions.prefetch_related("files").order_by("submitted_at", "id")
        for sequence, submission in enumerate(submissions, 1):
            student = safe_component(submission.student_name, "student", 60)
            directory = f"{root}/submissions/{sequence:04d}_{student}"
            used = set()
            if submission.answer_text:
                name = unique_name(f"{student} - webgui.txt", used)
                archive.writestr(f"{directory}/{name}", submission.answer_text.encode("utf-8"))
                rows.append(_manifest_row(sequence, submission, "webgui", "", name, len(submission.answer_text.encode("utf-8")), ""))
            for item in submission.files.all():
                original = safe_component(item.original_name, "attachment", 100)
                name = unique_name(f"{student} - attachment - {original}", used)
                archive.write(safe_absolute_path(item.storage_name), f"{directory}/{name}")
                rows.append(_manifest_row(sequence, submission, "attachment", item.original_name, name, item.size_bytes, item.sha256))

        manifest = io.StringIO(newline="")
        writer = csv.writer(manifest, lineterminator="\r\n")
        writer.writerow(["sequence", "submission_id", "receipt_id", "student_name", "submitted_at", "late", "content_type", "original_filename", "exported_filename", "size_bytes", "sha256"])
        writer.writerows(rows)
        archive.writestr(f"{root}/manifest.csv", "\ufeff" + manifest.getvalue())
    spool.seek(0)
    return spool, f"{root}.zip"


def _manifest_row(sequence, submission, content_type, original, exported, size, checksum):
    return [
        sequence,
        submission.id,
        csv_safe(submission.receipt_id),
        csv_safe(submission.student_name),
        submission.submitted_at.isoformat(),
        "yes" if submission.is_late else "no",
        content_type,
        csv_safe(original),
        csv_safe(exported),
        size,
        checksum,
    ]
