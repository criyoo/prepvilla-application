from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0036_appuser_gender"),
    ]

    operations = [
        migrations.AddField(
            model_name="appuser",
            name="student_profile_completed",
            field=models.BooleanField(default=False),
        ),
    ]
