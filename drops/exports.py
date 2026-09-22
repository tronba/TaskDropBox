import csv
import errno
import html
import re
import shutil
import tempfile
import zipfile
from pathlib import PurePosixPath

from django.conf import settings
from django.db.models import Count, Sum
from django.db.models.functions import Length
from django.utils import timezone
from django.utils.text import slugify

from .models import SubmissionFile
from .services import InsufficientStorageError
from .storage import ensure_space, safe_absolute_path
from .rich_text import rich_text_to_plain_text, sanitize_rich_text


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
    # Keep temporary output on the filesystem covered by the configured disk reserve.
    # This is a conservative estimate, not a reservation against concurrent uploads.
    submissions = task.submissions.prefetch_related("files").order_by("submitted_at", "id")
    totals = submissions.aggregate(count=Count("id"), text=Sum(Length("answer_text")))
    files = SubmissionFile.objects.filter(submission__task=task).aggregate(
        count=Count("id"), size=Sum("size_bytes")
    )
    projected = (
        (files["size"] or 0) * 1.01
        + (totals["text"] or 0) * 16
        + (totals["count"] + files["count"]) * 8192
        + 65536
    )
    if not ensure_space(projected):
        raise InsufficientStorageError
    spool = None
    try:
        spool = tempfile.TemporaryFile(mode="w+b", dir=settings.DATA_DIR)
        return _write_task_export(task, submissions, spool)
    except Exception as error:
        if spool is not None:
            spool.close()
        if isinstance(error, OSError) and error.errno in {errno.ENOSPC, errno.EDQUOT}:
            raise InsufficientStorageError from error
        raise


def _write_task_export(task, submissions, spool):
    date = timezone.localtime(task.created_at).strftime("%Y-%m-%d")
    root = f"{(slugify(task.title) or 'task')[:80]}_{date}"
    with (
        tempfile.TemporaryFile(
            mode="w+", encoding="utf-8-sig", newline="", dir=settings.DATA_DIR
        ) as manifest,
        zipfile.ZipFile(spool, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as archive,
    ):
        writer = csv.writer(manifest, lineterminator="\r\n")
        writer.writerow(["sequence", "submission_id", "receipt_id", "student_name", "submitted_at", "late", "content_type", "original_filename", "exported_filename", "size_bytes", "sha256"])
        # An explicit chunk size keeps prefetching bounded, including answer text.
        for sequence, submission in enumerate(submissions.iterator(chunk_size=50), 1):
            if not ensure_space(0):
                raise InsufficientStorageError
            student = safe_component(submission.student_name, "student", 60)
            directory = f"{root}/submissions/{sequence:04d}_{student}"
            used = set()
            if submission.answer_text:
                plain_answer = rich_text_to_plain_text(submission.answer_text)
                text_name = unique_name(f"{student} - webgui.txt", used)
                archive.writestr(f"{directory}/{text_name}", plain_answer.encode("utf-8"))
                writer.writerow(_manifest_row(sequence, submission, "webgui_text", "", text_name, len(plain_answer.encode("utf-8")), ""))
                html_name = unique_name(f"{student} - webgui.html", used)
                html_answer = formatted_answer_document(submission.student_name, submission.answer_text)
                archive.writestr(f"{directory}/{html_name}", html_answer)
                writer.writerow(_manifest_row(sequence, submission, "webgui_html", "", html_name, len(html_answer), ""))
            for item in submission.files.all():
                if not ensure_space(item.size_bytes * 1.01 + 4096):
                    raise InsufficientStorageError
                original = safe_component(item.original_name, "attachment", 100)
                name = unique_name(f"{student} - attachment - {original}", used)
                archive.write(safe_absolute_path(item.storage_name), f"{directory}/{name}")
                writer.writerow(_manifest_row(sequence, submission, "attachment", item.original_name, name, item.size_bytes, item.sha256))

        manifest.flush()
        manifest.buffer.seek(0)
        with archive.open(f"{root}/manifest.csv", "w", force_zip64=True) as destination:
            shutil.copyfileobj(manifest.buffer, destination, length=64 * 1024)
    if not ensure_space(0):
        raise InsufficientStorageError
    spool.seek(0)
    return spool, f"{root}.zip"


def formatted_answer_document(student_name, safe_answer_html):
    title = html.escape(f"Submission from {student_name}")
    safe_answer_html = sanitize_rich_text(safe_answer_html)
    document = (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        f"<title>{title}</title>"
        "<style>body{max-width:50rem;margin:3rem auto;padding:0 1rem;"
        "font:16px/1.55 system-ui,sans-serif;color:#172033}</style></head>"
        f"<body><h1>{title}</h1>{safe_answer_html}</body></html>"
    )
    return document.encode("utf-8")


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
