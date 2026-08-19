from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0028_platform_fee_transfer")]

    operations = [
        migrations.AddField(
            model_name="booking",
            name="student_completed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="booking",
            name="tutor_completed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
