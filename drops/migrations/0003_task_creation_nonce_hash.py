from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("drops", "0002_rich_text_content")]
    operations = [
        migrations.AddField(
            model_name="task",
            name="creation_nonce_hash",
            field=models.CharField(max_length=64, unique=True, null=True, editable=False),
        ),
    ]
