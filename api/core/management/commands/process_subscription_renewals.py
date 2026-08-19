from django.core.management.base import BaseCommand

from core.payments import process_due_subscription_renewals


class Command(BaseCommand):
    help = "Process due tutor and student subscription renewals."

    def handle(self, *args, **options):
        result = process_due_subscription_renewals()
        self.stdout.write(
            self.style.SUCCESS(
                "Checked {checked} subscription(s); renewed {renewed}; failed {failed}.".format(**result)
            )
        )
