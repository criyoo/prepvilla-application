from django.core.management.base import BaseCommand

from core.payments import process_ready_tutor_payouts


class Command(BaseCommand):
    help = "Release completed lesson payments to the tutor and PrepVilla operational account."

    def handle(self, *args, **options):
        result = process_ready_tutor_payouts()
        self.stdout.write(
            self.style.SUCCESS(
                "Checked {checked} paid booking(s); processed {processed}; failed {failed}; skipped {skipped}.".format(
                    **result
                )
            )
        )
