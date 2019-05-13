# -*- coding: utf-8 -*-

import inspect
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django_project.private_settings import DJANGO_PRIVATE_DATA

H_ULRICH_USER = User.objects.get(username='hprofdru')

EMAIL_MESSAGE_TXT = inspect.cleandoc("""Dear {},

Please visit https://imbc2.imb.uni-mainz.de:8443/approval_summary/ to check for new or modified records that need to be approved.

Best wishes,
The Ulrich lab intranet
""".format(H_ULRICH_USER.first_name))

send_mail(
    "Ulrich lab intranet weekly notification",
    EMAIL_MESSAGE_TXT,
    DJANGO_PRIVATE_DATA["server_email_address"],
    [H_ULRICH_USER.email],
)