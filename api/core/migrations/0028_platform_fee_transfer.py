from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [("core", "0027_payment_fields_and_flutterwave_models")]

    operations = [
        migrations.CreateModel(
            name="PlatformFeeTransfer",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("currency", models.CharField(default="NGN", max_length=3)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("queued", "Queued"),
                            ("processing", "Processing"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                        ],
                        default="queued",
                        max_length=20,
                    ),
                ),
                ("transfer_reference", models.CharField(blank=True, default="", max_length=120)),
                ("provider_transfer_id", models.CharField(blank=True, default="", max_length=120)),
                ("provider_payload", models.JSONField(blank=True, default=dict)),
                ("error_message", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "booking_payment",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="platform_fee_transfer",
                        to="core.bookingpayment",
                    ),
                ),
            ],
        ),
    ]
