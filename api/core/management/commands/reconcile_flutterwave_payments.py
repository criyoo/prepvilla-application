from django.core.management.base import BaseCommand

from core.payments import backfill_payment_accounting_records, reconcile_pending_customer_payments


class Command(BaseCommand):
    help = "Verify pending Flutterwave collections by transaction reference and update the local payment ledger."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        result = reconcile_pending_customer_payments(limit=max(options["limit"], 1))
        backfilled = backfill_payment_accounting_records()
        self.stdout.write(
            self.style.SUCCESS(
                "Checked {checked} pending payment(s); completed {completed}; still pending {pending}; failed {failed}.".format(
                    **result
                )
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Ledger synchronized for {subscriptions} subscription payment(s) and {lessons} lesson payment(s).".format(
                    **backfilled
                )
            )
        )
