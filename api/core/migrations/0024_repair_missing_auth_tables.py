from django.db import migrations


MISSING_AUTH_MODELS = [
    "AppUser",
    "TutorProfile",
    "OTP",
    "PasswordResetToken",
    "AccountFreezeRequest",
    "AccountDeleteRequest",
    "MeOtpChallenge",
    "PendingSignupChallenge",
    "MobileNumberChangeRequest",
    "StudentVerificationRequest",
]


def create_missing_auth_tables(apps, schema_editor):
    connection = schema_editor.connection
    existing_tables = set(connection.introspection.table_names())

    for model_name in MISSING_AUTH_MODELS:
        model = apps.get_model("core", model_name)
        table_name = model._meta.db_table
        if table_name in existing_tables:
            continue
        schema_editor.create_model(model)
        existing_tables.add(table_name)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0023_verification_residence_fields"),
    ]

    operations = [
        migrations.RunPython(
            create_missing_auth_tables,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
