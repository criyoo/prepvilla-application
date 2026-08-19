from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_tutorprofile_home_address_state_of_origin"),
    ]

    operations = [
        migrations.CreateModel(
            name="AccountFreezeRequest",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("starts_on", models.DateField()),
                ("ends_on", models.DateField()),
                ("code", models.CharField(max_length=6)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="freeze_requests", to="core.appuser")),
            ],
        ),
    ]

