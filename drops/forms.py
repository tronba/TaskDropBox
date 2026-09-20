import re

from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from .models import Task
from .rich_text import plain_text_to_html, rich_text_to_plain_text, sanitize_rich_text


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        single = super().clean
        if not data:
            return []
        return [single(item, initial) for item in data]


class CreatorPinForm(forms.Form):
    pin = forms.RegexField(
        regex=r"^[0-9]{6}$",
        label=_("Creator PIN"),
        widget=forms.PasswordInput(attrs={"inputmode": "numeric", "autocomplete": "off"}),
        error_messages={"invalid": _("Enter the six-digit creator PIN.")},
    )


class CapabilityForm(forms.Form):
    key = forms.CharField(max_length=1024, label=_("Task link or key"))


class TaskCreateForm(forms.ModelForm):
    creation_nonce = forms.RegexField(regex=r"^[A-Za-z0-9_-]{20,128}$", widget=forms.HiddenInput)
    due_at = forms.DateTimeField(
        required=False,
        label=_("Due date and time"),
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
        input_formats=["%Y-%m-%dT%H:%M"],
    )
    attachments = MultipleFileField(required=False, label=_("Task attachments"))

    class Meta:
        model = Task
        fields = ["title", "instructions_text", "due_at", "allow_text", "allow_files"]
        labels = {
            "title": _("Title"),
            "instructions_text": _("Instructions"),
            "allow_text": _("Allow answers written in TaskDropBox"),
            "allow_files": _("Allow file attachments"),
        }
        widgets = {
            "instructions_text": forms.Textarea(
                attrs={
                    "rows": 10,
                    "data-rich-text": "",
                    "data-bold-label": _("Bold"),
                    "data-italic-label": _("Italic"),
                    "data-bullet-list-label": _("Bulleted list"),
                    "data-numbered-list-label": _("Numbered list"),
                }
            )
        }

    def clean_instructions_text(self):
        value = self.cleaned_data["instructions_text"]
        if self.data.get("instructions_text_format") == "html":
            value = sanitize_rich_text(value)
        else:
            value = plain_text_to_html(value)
        if not rich_text_to_plain_text(value):
            raise forms.ValidationError(_("Enter task instructions."))
        return value

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("allow_text") and not cleaned.get("allow_files"):
            raise forms.ValidationError(_("Enable at least one answer type."))
        files = cleaned.get("attachments", [])
        if len(files) > settings.MAX_TASK_ATTACHMENTS:
            raise forms.ValidationError(_("Too many task attachments."))
        for uploaded in files:
            if uploaded.size > settings.MAX_FILE_BYTES:
                raise forms.ValidationError(_("A task attachment is too large."))
        return cleaned


class SubmissionForm(forms.Form):
    idempotency_key = forms.RegexField(
        regex=r"^[A-Za-z0-9_-]{20,128}$", widget=forms.HiddenInput
    )
    student_name = forms.CharField(max_length=150, label=_("Your name"))
    answer_text = forms.CharField(
        required=False,
        max_length=100_000,
        label=_("Written answer"),
        widget=forms.Textarea(
            attrs={
                "rows": 12,
                "data-rich-text": "",
                "data-bold-label": _("Bold"),
                "data-italic-label": _("Italic"),
                "data-bullet-list-label": _("Bulleted list"),
                "data-numbered-list-label": _("Numbered list"),
            }
        ),
    )
    files = MultipleFileField(required=False, label=_("Attachments"))

    def __init__(self, *args, task, **kwargs):
        self.task = task
        super().__init__(*args, **kwargs)
        if not task.allow_text:
            self.fields.pop("answer_text")
        if not task.allow_files:
            self.fields.pop("files")

    def clean_student_name(self):
        name = re.sub(r"\s+", " ", self.cleaned_data["student_name"].strip())
        if not name:
            raise forms.ValidationError(_("Enter your name."))
        return name

    def clean_answer_text(self):
        answer = self.cleaned_data["answer_text"].strip()
        if not answer:
            return ""
        if self.data.get("answer_text_format") == "html":
            answer = sanitize_rich_text(answer)
        else:
            answer = plain_text_to_html(answer)
        if not rich_text_to_plain_text(answer):
            return ""
        if len(answer) > 100_000:
            raise forms.ValidationError(_("The formatted answer is too long."))
        return answer

    def clean(self):
        cleaned = super().clean()
        answer = cleaned.get("answer_text", "")
        files = cleaned.get("files", [])
        if not answer and not files:
            raise forms.ValidationError(_("Write an answer or attach at least one file."))
        if len(files) > settings.MAX_FILES_PER_SUBMISSION:
            raise forms.ValidationError(_("Too many attached files."))
        total = 0
        for uploaded in files:
            if uploaded.size > settings.MAX_FILE_BYTES:
                raise forms.ValidationError(_("An attached file is too large."))
            total += uploaded.size
        if total > settings.MAX_SUBMISSION_BYTES:
            raise forms.ValidationError(_("The combined attachments are too large."))
        return cleaned
