from django.db import migrations, models


def normalize_legacy_verification_statuses(apps, schema_editor):
    TutorProfile = apps.get_model("core", "TutorProfile")
    VerificationRequest = apps.get_model("core", "VerificationRequest")

    TutorProfile.objects.filter(verification_status="verified").update(verification_status="approved")
    VerificationRequest.objects.filter(status="verified").update(status="approved")


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0018_pendingsignupchallenge"),
    ]

    operations = [
        migrations.AddField(
            model_name="tutorprofile",
            name="additional_document_urls",
            field=models.TextField(
                blank=True,
                default="",
                help_text="JSON encoded list of additional supporting document URLs",
            ),
        ),
        migrations.AddField(
            model_name="tutorprofile",
            name="offers_face_to_face",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="tutorprofile",
            name="offers_webcam",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(
            normalize_legacy_verification_statuses,
            migrations.RunPython.noop,
        ),
    ]
