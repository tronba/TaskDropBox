import html

from django.db import migrations


def plain_text_to_html(value):
    normalized = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    if not normalized:
        return ""
    return "".join(
        f"<p>{html.escape(paragraph).replace(chr(10), '<br>')}</p>"
        for paragraph in normalized.split("\n\n")
    )


def convert_existing_content(apps, schema_editor):
    Task = apps.get_model("drops", "Task")
    Submission = apps.get_model("drops", "Submission")
    for task in Task.objects.all().iterator():
        task.instructions_text = plain_text_to_html(task.instructions_text)
        task.save(update_fields=["instructions_text"])
    for submission in Submission.objects.all().iterator():
        submission.answer_text = plain_text_to_html(submission.answer_text)
        submission.save(update_fields=["answer_text"])


class Migration(migrations.Migration):
    dependencies = [("drops", "0001_initial")]
    operations = [migrations.RunPython(convert_existing_content, migrations.RunPython.noop)]
