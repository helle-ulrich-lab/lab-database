from django.apps import AppConfig
from django.db.models.signals import post_save


class UserManagementConfig(AppConfig):
    name = "extend_user"

    def ready(self):
        from django.contrib.auth.models import User

        from .signals import create_labuser

        post_save.connect(create_labuser, sender=User)
