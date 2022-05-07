from django.apps import AppConfig
from django.db.models.signals import post_save

class UserManagementConfig(AppConfig):
    name = 'user_management'

    def ready(self):
        from .signals import create_labuser
        from django.contrib.auth.models import User

        post_save.connect(create_labuser, sender=User)