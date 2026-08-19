from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0009_account_delete_request"),
    ]

    operations = [
        migrations.CreateModel(
            name="MeOtpChallenge",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("purpose", models.CharField(max_length=50)),
                ("payload", models.TextField(blank=True, default="")),
                ("code_salt", models.CharField(max_length=32)),
                ("code_hash", models.CharField(max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="me_otp_challenges", to="core.appuser")),
            ],
        ),
    ]

