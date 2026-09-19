import hashlib
import os
import re
import shutil
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation


@dataclass(frozen=True)
class PreparedUpload:
    temporary_path: Path
    original_name: str
    size_bytes: int
    content_type: str
    sha256: str


def normalized_name(name):
    name = str(name).replace("\\", "/").split("/")[-1]
    name = re.sub(r"[\x00-\x1f\x7f]", "", name).strip().strip(".")
    return (name or "unnamed-file")[:255]


def ensure_space(projected_bytes):
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(settings.DATA_DIR).free
    return free - projected_bytes >= settings.MIN_FREE_DISK_BYTES


def prepare_upload(uploaded, max_bytes):
    temporary_dir = settings.PRIVATE_FILES_DIR / ".tmp"
    temporary_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    size = 0
    handle, path = tempfile.mkstemp(prefix="upload-", dir=temporary_dir)
    try:
        with os.fdopen(handle, "wb") as destination:
            for chunk in uploaded.chunks():
                if size + len(chunk) > max_bytes:
                    raise UploadTooLargeError
                destination.write(chunk)
                digest.update(chunk)
                size += len(chunk)
        return PreparedUpload(
            temporary_path=Path(path),
            original_name=normalized_name(uploaded.name),
            size_bytes=size,
            content_type=(getattr(uploaded, "content_type", "") or "")[:255],
            sha256=digest.hexdigest(),
        )
    except Exception:
        Path(path).unlink(missing_ok=True)
        raise


def commit_upload(prepared, category):
    relative = Path(category) / uuid.uuid4().hex
    destination = safe_absolute_path(relative.as_posix())
    destination.parent.mkdir(parents=True, exist_ok=True)
    os.replace(prepared.temporary_path, destination)
    return relative.as_posix()


def safe_absolute_path(storage_name):
    root = settings.PRIVATE_FILES_DIR.resolve()
    candidate = (root / storage_name).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise SuspiciousFileOperation("File path escapes private storage") from exc
    return candidate


def remove_storage_name(storage_name):
    safe_absolute_path(storage_name).unlink(missing_ok=True)


def discard_prepared(prepared_uploads):
    for prepared in prepared_uploads:
        prepared.temporary_path.unlink(missing_ok=True)


def stage_deletions(storage_names):
    trash = settings.PRIVATE_FILES_DIR / ".trash" / uuid.uuid4().hex
    staged = []
    try:
        for storage_name in storage_names:
            source = safe_absolute_path(storage_name)
            if not source.exists():
                continue
            destination = trash / storage_name
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(source, destination)
            staged.append((source, destination))
        return trash, staged
    except Exception:
        restore_staged(staged)
        purge_trash(trash, ignore_errors=True)
        raise


def restore_staged(staged):
    for source, destination in reversed(staged):
        if destination.exists():
            source.parent.mkdir(parents=True, exist_ok=True)
            os.replace(destination, source)


def purge_trash(trash, *, ignore_errors=False):
    if trash.exists():
        shutil.rmtree(trash, ignore_errors=ignore_errors)


class UploadTooLargeError(Exception):
    pass
