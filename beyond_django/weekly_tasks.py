# -*- coding: utf-8 -*-

import inspect
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django_project.private_settings import DJANGO_PRIVATE_DATA
from django_project.settings import SITE_TITLE
from django.urls import reverse

PI_USER = User.objects.get(labuser__is_principal_investigator=True)

RECORD_APPROVAL_URL = reverse("admin:record_approval_recordtobeapproved_changelist")

EMAIL_MESSAGE_TXT = inspect.cleandoc("""Dear {},

Please visit https://{}{} to check for new or modified records that need to be approved.

Best wishes,
The {}
""".format(PI_USER.first_name, DJANGO_PRIVATE_DATA['allowed_hosts'][0], RECORD_APPROVAL_URL, SITE_TITLE))

send_mail(
    "{} weekly notification".format(SITE_TITLE),
    EMAIL_MESSAGE_TXT,
    DJANGO_PRIVATE_DATA["server_email_address"],
    [PI_USER.email],
)

# Delete all completed tasks

from background_task.models_completed import CompletedTask
CompletedTask.objects.all().delete()