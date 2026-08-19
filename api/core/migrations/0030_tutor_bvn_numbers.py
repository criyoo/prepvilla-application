from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0029_booking_completion_confirmations"),
    ]

    operations = [
        migrations.AddField(
            model_name="tutorprofile",
            name="bvn_number",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AddField(
            model_name="verificationrequest",
            name="bvn_number",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
    ]
