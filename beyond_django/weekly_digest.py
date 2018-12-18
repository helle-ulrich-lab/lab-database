# -*- coding: utf-8 -*-

import smtplib
import inspect

def send_email(text):
    user = None
    pwd = None
    FROM = "system@imbc2.imb.uni-mainz.de"
    TO = ['H.Ulrich@imb-mainz.de'] #must be a list
    SUBJECT = "Ulrich lab intranet weekly notification"
    message = """\From: %s\nTo: %s\nSubject: %s\n\n%s""" % (FROM, ", ".join(TO), SUBJECT, text)
    server = smtplib.SMTP("localhost", 25)
    server.sendmail(FROM, TO, message.encode('utf8'))
    server.close()

EMAIL_MESSAGE_TXT = inspect.cleandoc("""Dear Helle,

Please visit https://imbc2.imb.uni-mainz.de:8443/approval_summary/ to check for new or modified records that need to be approved.

Best wishes,
The Ulrich lab intranet
""")
send_email(EMAIL_MESSAGE_TXT)