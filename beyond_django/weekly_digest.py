# -*- coding: utf-8 -*-

import inspect
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django_project.private_settings import DJANGO_PRIVATE_DATA
from django.urls import reverse

HU_USER = User.objects.get(labuser__is_principal_investigator=True) # Helle's user object

RECORD_APPROVAL_URL = reverse("admin:record_approval_recordtobeapproved_changelist")

EMAIL_MESSAGE_TXT = inspect.cleandoc("""Dear {},

Please visit https://{}{} to check for new or modified records that need to be approved.

Best wishes,
The Ulrich lab intranet
""".format(HU_USER.first_name, DJANGO_PRIVATE_DATA['allowed_hosts'][0], RECORD_APPROVAL_URL))

send_mail(
    "Ulrich lab intranet weekly notification",
    EMAIL_MESSAGE_TXT,
    DJANGO_PRIVATE_DATA["server_email_address"],
    [HU_USER.email],
)

# Delete all completed tasks

from background_task.models_completed import CompletedTask
CompletedTask.objects.all().delete()