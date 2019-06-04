# -*- coding: utf-8 -*-

import inspect
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django_project.private_settings import DJANGO_PRIVATE_DATA

H_ULRICH_USER = User.objects.get(username='hprofdru')

EMAIL_MESSAGE_TXT = inspect.cleandoc("""Dear {},

Please visit https://{}/approval_summary/ to check for new or modified records that need to be approved.

Best wishes,
The Ulrich lab intranet
""".format(H_ULRICH_USER.first_name, DJANGO_PRIVATE_DATA['allowed_hosts'][0]))

send_mail(
    "Ulrich lab intranet weekly notification",
    EMAIL_MESSAGE_TXT,
    DJANGO_PRIVATE_DATA["server_email_address"],
    [H_ULRICH_USER.email],
)

# Delete all completed tasks

from background_task.models_completed import CompletedTask
CompletedTask.objects.all().delete()