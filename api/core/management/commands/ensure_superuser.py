from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create or update a superuser with a known password."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="Superuser email")
        parser.add_argument("--password", required=True, help="Superuser password")
        parser.add_argument("--display-name", default="Admin", help="Display name")
        parser.add_argument("--full-name", default="Admin", help="Full name")
        parser.add_argument("--timezone", default="UTC", help="User timezone")

    def handle(self, *args, **options):
        user_model = get_user_model()
        email = user_model.objects.normalize_email(options["email"])
        password = options["password"]

        defaults = {
            "role": "admin",
            "display_name": options["display_name"],
            "full_name": options["full_name"],
            "timezone": options["timezone"],
            "is_staff": True,
            "is_superuser": True,
            "is_verified": True,
            "is_active": True,
        }

        user, created = user_model.objects.get_or_create(email=email, defaults=defaults)

        fields_to_update = []
        for field, value in defaults.items():
            if getattr(user, field) != value:
                setattr(user, field, value)
                fields_to_update.append(field)

        user.set_password(password)
        fields_to_update.append("password")
        user.save(update_fields=sorted(set(fields_to_update)))

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created superuser {email}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Updated superuser {email}"))
