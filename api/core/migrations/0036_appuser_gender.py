from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0035_verification_status_labels"),
    ]

    operations = [
        migrations.AddField(
            model_name="appuser",
            name="gender",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
    ]
