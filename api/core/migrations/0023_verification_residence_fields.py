from django.db import migrations, models


def backfill_verification_residence(apps, schema_editor):
    VerificationRequest = apps.get_model("core", "VerificationRequest")
    db_alias = schema_editor.connection.alias

    for verification in (
        VerificationRequest.objects.using(db_alias)
        .select_related("tutor_profile__user")
        .all()
    ):
        tutor_profile = verification.tutor_profile
        tutor_user = tutor_profile.user
        verification.home_state = (
            (verification.home_state or "").strip()
            or (tutor_profile.home_state or "").strip()
            or (tutor_user.state or "").strip()
        )
        verification.home_city = (
            (verification.home_city or "").strip()
            or (tutor_profile.home_city or "").strip()
            or (tutor_user.location or "").strip()
        )
        verification.home_address = (
            (verification.home_address or "").strip()
            or (tutor_profile.home_address or "").strip()
            or (tutor_user.address or "").strip()
        )
        verification.save(update_fields=["home_state", "home_city", "home_address"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0022_performance_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="verificationrequest",
            name="home_address",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="verificationrequest",
            name="home_city",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="verificationrequest",
            name="home_state",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.RunPython(backfill_verification_residence, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="tutorprofile",
            name="principal_name",
        ),
        migrations.RemoveField(
            model_name="tutorprofile",
            name="school_address",
        ),
        migrations.RemoveField(
            model_name="tutorprofile",
            name="school_name",
        ),
        migrations.RemoveField(
            model_name="verificationrequest",
            name="principal_name",
        ),
        migrations.RemoveField(
            model_name="verificationrequest",
            name="school_address",
        ),
        migrations.RemoveField(
            model_name="verificationrequest",
            name="school_name",
        ),
    ]
