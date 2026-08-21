from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0034_student_verification_details"),
    ]

    operations = [
        migrations.AlterField(
            model_name="studentverificationrequest",
            name="status",
            field=models.CharField(
                choices=[("pending", "Pending"), ("approved", "Verified"), ("rejected", "Rejected")],
                default="pending",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="verificationrequest",
            name="status",
            field=models.CharField(
                choices=[("pending", "Pending"), ("approved", "Verified"), ("rejected", "Rejected")],
                default="pending",
                max_length=20,
            ),
        ),
    ]
