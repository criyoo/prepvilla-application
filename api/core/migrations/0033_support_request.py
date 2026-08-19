import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0032_payment_ledger_and_webhook_events"),
    ]

    operations = [
        migrations.CreateModel(
            name="SupportRequest",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("kind", models.CharField(choices=[("feedback", "Feedback"), ("complaint", "Complaint"), ("issue", "Issue")], max_length=20)),
                ("status", models.CharField(choices=[("open", "Open"), ("in_progress", "In progress"), ("resolved", "Resolved"), ("closed", "Closed")], default="open", max_length=20)),
                ("priority", models.CharField(choices=[("normal", "Normal"), ("high", "High"), ("urgent", "Urgent")], default="normal", max_length=20)),
                ("role", models.CharField(max_length=20)),
                ("topic", models.CharField(max_length=160)),
                ("message", models.TextField()),
                ("related_reference", models.CharField(blank=True, default="", max_length=160)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("admin_notes", models.TextField(blank=True, default="")),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assigned_to", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assigned_support_requests", to="core.appuser")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="support_requests", to="core.appuser")),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.AddIndex(
            model_name="supportrequest",
            index=models.Index(fields=["kind", "status", "-created_at"], name="core_support_kind_status_idx"),
        ),
        migrations.AddIndex(
            model_name="supportrequest",
            index=models.Index(fields=["user", "-created_at"], name="core_support_user_created_idx"),
        ),
        migrations.AddIndex(
            model_name="supportrequest",
            index=models.Index(fields=["priority", "status"], name="core_support_priority_idx"),
        ),
    ]
