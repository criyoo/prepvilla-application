import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0031_tutor_biodata_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscriptionpayment",
            name="payment_method",
            field=models.CharField(blank=True, default="", max_length=40),
        ),
        migrations.AddField(
            model_name="bookingpayment",
            name="held_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="bookingpayment",
            name="payment_method",
            field=models.CharField(blank=True, default="", max_length=40),
        ),
        migrations.AddField(
            model_name="bookingpayment",
            name="platform_fee_amount",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name="bookingpayment",
            name="released_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="bookingpayment",
            name="tutor_amount",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name="tutorpayout",
            name="completed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="tutorpayout",
            name="failed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="tutorpayout",
            name="processed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterModelOptions(
            name="platformfeetransfer",
            options={"verbose_name": "platform fee", "verbose_name_plural": "platform fees"},
        ),
        migrations.CreateModel(
            name="PaymentWebhookEvent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("event_key", models.CharField(max_length=64, unique=True)),
                ("provider_event_id", models.CharField(blank=True, db_index=True, default="", max_length=120)),
                ("event_type", models.CharField(blank=True, db_index=True, default="", max_length=80)),
                ("transaction_reference", models.CharField(blank=True, db_index=True, default="", max_length=160)),
                ("provider_transaction_id", models.CharField(blank=True, db_index=True, default="", max_length=120)),
                ("transfer_reference", models.CharField(blank=True, db_index=True, default="", max_length=160)),
                ("status", models.CharField(choices=[("received", "Received"), ("processing", "Processing"), ("processed", "Processed"), ("ignored", "Ignored"), ("failed", "Failed")], default="received", max_length=20)),
                ("payload", models.JSONField(default=dict)),
                ("error_message", models.TextField(blank=True, default="")),
                ("received_at", models.DateTimeField(auto_now_add=True)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ("-received_at",)},
        ),
        migrations.CreateModel(
            name="PaymentLedgerEntry",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("reference", models.CharField(max_length=160, unique=True)),
                ("entry_type", models.CharField(choices=[("subscription_collection", "Subscription collection"), ("lesson_collection", "Lesson collection"), ("platform_fee", "PrepVilla fee"), ("tutor_payable", "Tutor payable"), ("tutor_payout", "Tutor payout")], max_length=40)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("held", "Held"), ("available", "Available"), ("processing", "Processing"), ("completed", "Completed"), ("failed", "Failed")], default="pending", max_length=20)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("currency", models.CharField(default="NGN", max_length=3)),
                ("provider_reference", models.CharField(blank=True, db_index=True, default="", max_length=120)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("booking_payment", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="ledger_entries", to="core.bookingpayment")),
                ("subscription_payment", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="ledger_entries", to="core.subscriptionpayment")),
                ("tutor_payout", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="ledger_entries", to="core.tutorpayout")),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.AddIndex(
            model_name="paymentwebhookevent",
            index=models.Index(fields=["event_type", "status"], name="core_webhook_type_status_idx"),
        ),
        migrations.AddIndex(
            model_name="paymentledgerentry",
            index=models.Index(fields=["entry_type", "status"], name="core_ledger_type_status_idx"),
        ),
        migrations.AddIndex(
            model_name="paymentledgerentry",
            index=models.Index(fields=["booking_payment", "entry_type"], name="core_ledger_booking_type_idx"),
        ),
    ]
