from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.http import FileResponse, Http404, HttpResponse
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from .auth import (
    authorize_creator,
    creator_is_authorized,
    grant_task_admin,
    has_task_admin,
    verify_creator_pin,
)
from .forms import CapabilityForm, CreatorPinForm, SubmissionForm, TaskCreateForm
from .models import Submission, SubmissionFile, Task, TaskAttachment
from .rate_limits import (
    creator_pin_is_allowed,
    record_creator_pin_failure,
    reset_creator_pin_failures,
)
from .exports import build_task_export
from .services import (
    InsufficientStorageError,
    InvalidIdempotencyKeyError,
    TaskClosedError,
    create_submission,
    create_task,
    delete_submission,
    delete_task,
)
from .storage import UploadTooLargeError, safe_absolute_path
from .tokens import digest_token, extract_key, new_form_nonce

CREATION_NONCES_SESSION_KEY = "task_creation_nonces"


def creator_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not creator_is_authorized(request):
            return redirect("creator_login")
        return view(request, *args, **kwargs)

    return wrapped


def admin_task_or_404(request, task_id):
    if not has_task_admin(request, task_id):
        raise Http404
    return get_object_or_404(Task, pk=task_id)


@require_GET
def home(request):
    return render(
        request,
        "drops/home.html",
        {
            "creator_form": CreatorPinForm(),
            "student_form": CapabilityForm(prefix="student"),
            "admin_form": CapabilityForm(prefix="admin"),
        },
    )


def creator_login(request):
    form = CreatorPinForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if not creator_pin_is_allowed():
            return render(request, "drops/rate_limited.html", status=429)
        if verify_creator_pin(form.cleaned_data["pin"]):
            reset_creator_pin_failures()
            authorize_creator(request)
            return redirect("task_create")
        record_creator_pin_failure()
        form.add_error("pin", _("The creator PIN was not accepted."))
    return render(request, "drops/creator_login.html", {"form": form})


@creator_required
def task_create(request):
    if request.method == "GET":
        nonce = new_form_nonce()
        nonces = request.session.get(CREATION_NONCES_SESSION_KEY, [])[-4:]
        request.session[CREATION_NONCES_SESSION_KEY] = [*nonces, digest_token(nonce)]
        form = TaskCreateForm(initial={"creation_nonce": nonce})
    else:
        form = TaskCreateForm(request.POST, request.FILES)
    if request.method == "POST" and form.is_valid():
        nonce_hash = digest_token(form.cleaned_data["creation_nonce"])
        nonces = request.session.get(CREATION_NONCES_SESSION_KEY, [])
        if nonce_hash not in nonces:
            form.add_error(None, _("This creation form was already used or has expired."))
            return render(request, "drops/task_create.html", {"form": form}, status=409)
        try:
            task, student_token, admin_token = create_task(
                form.cleaned_data, form.cleaned_data.get("attachments", [])
            )
        except InsufficientStorageError:
            return render(request, "drops/storage_unavailable.html", status=503)
        except UploadTooLargeError:
            form.add_error("attachments", _("One or more attachments exceeded the upload limits."))
            return render(request, "drops/task_create.html", {"form": form}, status=413)
        request.session[CREATION_NONCES_SESSION_KEY] = [
            value for value in nonces if value != nonce_hash
        ]
        return render(
            request,
            "drops/task_created.html",
            {
                "task": task,
                "student_url": f"{settings.BASE_URL}/d/{student_token}/",
                "admin_url": f"{settings.BASE_URL}/a/{admin_token}/",
            },
        )
    return render(request, "drops/task_create.html", {"form": form})


@require_POST
def open_student(request):
    form = CapabilityForm(request.POST, prefix="student")
    if form.is_valid():
        key = extract_key(form.cleaned_data["key"], "d")
        if key and Task.objects.filter(student_token_hash=digest_token(key)).exists():
            return redirect("student_task", student_token=key)
    messages.error(request, _("That student task link or key was not accepted."))
    return redirect("home")


@require_POST
def open_admin(request):
    form = CapabilityForm(request.POST, prefix="admin")
    if form.is_valid():
        key = extract_key(form.cleaned_data["key"], "a")
        if key:
            task = Task.objects.filter(admin_token_hash=digest_token(key)).first()
            if task:
                grant_task_admin(request, task.id)
                return redirect("manage_task", task_id=task.id)
    messages.error(request, _("That teacher task link or key was not accepted."))
    return redirect("home")


def task_by_student_token(raw_token):
    task = Task.objects.filter(student_token_hash=digest_token(raw_token)).first()
    if not task:
        raise Http404
    return task


@require_GET
def student_task(request, student_token):
    task = task_by_student_token(student_token)
    form = SubmissionForm(task=task, initial={"idempotency_key": new_form_nonce()})
    return render(
        request,
        "drops/student_task.html",
        {"task": task, "form": form, "now": timezone.now()},
    )


@require_POST
def submit_task(request, student_token):
    task = task_by_student_token(student_token)
    if task.status != Task.Status.OPEN:
        return render(request, "drops/task_closed.html", {"task": task}, status=409)
    form = SubmissionForm(request.POST, request.FILES, task=task)
    if not form.is_valid():
        return render(
            request,
            "drops/student_task.html",
            {"task": task, "form": form, "now": timezone.now()},
            status=400,
        )
    try:
        submission = create_submission(task, form.cleaned_data, form.cleaned_data.get("files", []))
    except TaskClosedError:
        return render(request, "drops/task_closed.html", {"task": task}, status=409)
    except InsufficientStorageError:
        return render(request, "drops/storage_unavailable.html", status=503)
    except InvalidIdempotencyKeyError:
        raise Http404
    except UploadTooLargeError:
        form.add_error("files", _("One or more attachments exceeded the upload limits."))
        return render(
            request,
            "drops/student_task.html",
            {"task": task, "form": form, "now": timezone.now()},
            status=413,
        )
    return redirect("submission_receipt", receipt_id=submission.receipt_id)


@require_GET
def submission_receipt(request, receipt_id):
    submission = get_object_or_404(Submission.objects.select_related("task"), receipt_id=receipt_id)
    return render(request, "drops/submission_receipt.html", {"submission": submission})


@require_GET
def task_attachment_download(request, student_token, file_id):
    task = task_by_student_token(student_token)
    item = get_object_or_404(TaskAttachment, pk=file_id, task=task)
    return private_file_response(item)


@require_GET
def admin_exchange(request, admin_token):
    task = Task.objects.filter(admin_token_hash=digest_token(admin_token)).first()
    if not task:
        raise Http404
    grant_task_admin(request, task.id)
    return redirect("manage_task", task_id=task.id)


@require_GET
def manage_task(request, task_id):
    task = admin_task_or_404(request, task_id)
    queryset = task.submissions.prefetch_related("files").all()
    submissions = Paginator(queryset, 50).get_page(request.GET.get("page"))
    return render(
        request, "drops/manage_task.html", {"task": task, "submissions": submissions}
    )


@require_POST
def close_task(request, task_id):
    task = admin_task_or_404(request, task_id)
    task.status = Task.Status.CLOSED
    task.closed_at = timezone.now()
    task.save(update_fields=["status", "closed_at"])
    return redirect("manage_task", task_id=task.id)


@require_POST
def reopen_task(request, task_id):
    task = admin_task_or_404(request, task_id)
    task.status = Task.Status.OPEN
    task.closed_at = None
    task.save(update_fields=["status", "closed_at"])
    return redirect("manage_task", task_id=task.id)


@require_GET
def submission_file_download(request, task_id, file_id):
    task = admin_task_or_404(request, task_id)
    item = get_object_or_404(
        SubmissionFile.objects.select_related("submission"), pk=file_id, submission__task=task
    )
    return private_file_response(item)


@require_GET
def admin_task_attachment_download(request, task_id, file_id):
    task = admin_task_or_404(request, task_id)
    item = get_object_or_404(TaskAttachment, pk=file_id, task=task)
    return private_file_response(item)


@require_GET
def export_task(request, task_id):
    task = admin_task_or_404(request, task_id)
    spool, filename = build_task_export(task)
    return FileResponse(spool, as_attachment=True, filename=filename, content_type="application/zip")


@require_http_methods(["GET", "POST"])
def delete_submission_view(request, task_id, submission_id):
    task = admin_task_or_404(request, task_id)
    submission = get_object_or_404(Submission, pk=submission_id, task=task)
    if request.method == "POST":
        delete_submission(submission)
        return redirect("manage_task", task_id=task.id)
    return render(request, "drops/confirm_delete_submission.html", {"task": task, "submission": submission})


@require_http_methods(["GET", "POST"])
def delete_task_view(request, task_id):
    task = admin_task_or_404(request, task_id)
    if request.method == "POST":
        delete_task(task)
        messages.success(request, _("The task and all of its live content were deleted."))
        return redirect("home")
    return render(request, "drops/confirm_delete_task.html", {"task": task})


def private_file_response(item):
    path = safe_absolute_path(item.storage_name)
    if not path.is_file():
        raise Http404
    response = FileResponse(path.open("rb"), as_attachment=True, filename=item.original_name)
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@require_GET
def health(request):
    return HttpResponse("ok\n", content_type="text/plain")


@require_GET
def source_archive(request):
    if not settings.SOURCE_ARCHIVE.is_file():
        raise Http404
    return FileResponse(
        settings.SOURCE_ARCHIVE.open("rb"),
        as_attachment=True,
        filename="taskdropbox-source.tar.gz",
        content_type="application/gzip",
    )


def not_found(request, exception):
    return render(request, "404.html", status=404)


def server_error(request):
    return render(
        request,
        "500.html",
        {"correlation_id": getattr(request, "correlation_id", _("unavailable"))},
        status=500,
    )
