from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [("core", "0026_seededstudentaccount")]

    operations = [
        migrations.AddField(model_name="tutorprofile", name="bank_name", field=models.CharField(blank=True, default="", max_length=120)),
        migrations.AddField(model_name="tutorprofile", name="bank_code", field=models.CharField(blank=True, default="", max_length=20)),
        migrations.AddField(model_name="tutorprofile", name="bank_account_number", field=models.CharField(blank=True, default="", max_length=20)),
        migrations.AddField(model_name="tutorprofile", name="bank_account_name", field=models.CharField(blank=True, default="", max_length=160)),
        migrations.AddField(model_name="tutorprofile", name="flutterwave_subaccount_id", field=models.CharField(blank=True, default="", max_length=80)),
        migrations.AddField(model_name="studentverificationrequest", name="nin_number", field=models.CharField(blank=True, default="", max_length=20)),
        migrations.CreateModel(
            name="SubscriptionPayment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("plan", models.CharField(max_length=80)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("currency", models.CharField(default="NGN", max_length=3)),
                ("provider", models.CharField(default="flutterwave", max_length=40)),
                ("transaction_id", models.CharField(max_length=120, unique=True)),
                ("provider_transaction_id", models.CharField(blank=True, default="", max_length=120)),
                ("payment_link", models.URLField(blank=True, default="")),
                ("status", models.CharField(choices=[("pending", "Pending"), ("completed", "Completed"), ("failed", "Failed"), ("cancelled", "Cancelled")], default="pending", max_length=20)),
                ("provider_payload", models.JSONField(blank=True, default=dict)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="subscription_payments", to="core.appuser")),
            ],
            options={"indexes": [models.Index(fields=["user", "created_at"], name="core_subpay_user_created_idx"), models.Index(fields=["status", "created_at"], name="core_subpay_status_created_idx")]},
        ),
        migrations.CreateModel(
            name="BookingPayment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("currency", models.CharField(default="NGN", max_length=3)),
                ("provider", models.CharField(default="flutterwave", max_length=40)),
                ("transaction_id", models.CharField(max_length=120, unique=True)),
                ("provider_transaction_id", models.CharField(blank=True, default="", max_length=120)),
                ("payment_link", models.URLField(blank=True, default="")),
                ("status", models.CharField(choices=[("pending", "Pending"), ("completed", "Completed"), ("failed", "Failed"), ("cancelled", "Cancelled")], default="pending", max_length=20)),
                ("provider_payload", models.JSONField(blank=True, default=dict)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("booking", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="payment", to="core.booking")),
                ("student_user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="booking_payments", to="core.appuser")),
                ("tutor_profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="booking_payments", to="core.tutorprofile")),
            ],
            options={"indexes": [models.Index(fields=["student_user", "created_at"], name="core_bookpay_student_ct_idx"), models.Index(fields=["tutor_profile", "status"], name="core_bookpay_tutor_status_idx")]},
        ),
        migrations.CreateModel(
            name="TutorPayout",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("currency", models.CharField(default="NGN", max_length=3)),
                ("status", models.CharField(choices=[("queued", "Queued"), ("processing", "Processing"), ("completed", "Completed"), ("failed", "Failed")], default="queued", max_length=20)),
                ("transfer_reference", models.CharField(blank=True, default="", max_length=120)),
                ("provider_transfer_id", models.CharField(blank=True, default="", max_length=120)),
                ("provider_payload", models.JSONField(blank=True, default=dict)),
                ("error_message", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("booking_payment", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="tutor_payout", to="core.bookingpayment")),
                ("tutor_profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="payouts", to="core.tutorprofile")),
            ],
        ),
    ]
