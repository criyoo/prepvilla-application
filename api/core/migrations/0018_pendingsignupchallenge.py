from django.db import migrations, models
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0017_role_proxy_users"),
    ]

    operations = [
        migrations.CreateModel(
            name="PendingSignupChallenge",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("email", models.EmailField(db_index=True, max_length=254)),
                ("role", models.CharField(max_length=20)),
                ("full_name", models.CharField(max_length=255)),
                ("password_hash", models.CharField(max_length=255)),
                ("code_salt", models.CharField(max_length=32)),
                ("code_hash", models.CharField(max_length=64)),
                ("attempts", models.IntegerField(default=0)),
                ("expires_at", models.DateTimeField()),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
