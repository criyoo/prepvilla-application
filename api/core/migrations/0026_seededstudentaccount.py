from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0025_seedtutoraccount"),
    ]

    operations = [
        migrations.CreateModel(
            name="SeededStudentAccount",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("seed_key", models.CharField(max_length=120, unique=True)),
                ("source_hash", models.CharField(blank=True, default="", max_length=64)),
                ("managed_paths", models.TextField(blank=True, default="", help_text="JSON encoded list of storage paths managed by the seed sync")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="seeded_student_account", to="core.appuser")),
            ],
        ),
    ]
