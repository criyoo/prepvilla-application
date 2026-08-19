from django.apps import AppConfig
from django.db.models.signals import post_migrate


class CoreConfig(AppConfig):
  default_auto_field = "django.db.models.BigAutoField"
  name = "core"

  def ready(self):
    from .seed_demo_data import (
      seed_demo_accounts_students_after_migrate,
      seed_demo_accounts_tutors_after_migrate,
    )

    post_migrate.connect(
      seed_demo_accounts_tutors_after_migrate,
      sender=self,
      dispatch_uid="core.seed_demo_accounts_tutors_after_migrate",
    )
    post_migrate.connect(
      seed_demo_accounts_students_after_migrate,
      sender=self,
      dispatch_uid="core.seed_demo_accounts_students_after_migrate",
    )
