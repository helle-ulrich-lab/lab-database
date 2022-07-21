#################################################
#    DJANGO 'CORE' FUNCTIONALITIES IMPORTS      #
#################################################

from django.db import models
from django.contrib.auth.models import User

#################################################
#        EXTENDED LAB MEMEBER USER MODEL        #
#################################################

class LabUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.PROTECT)
    is_principal_investigator = models.BooleanField('is principal investigator?', default=False)
    oidc_identifier = models.CharField("OIDC identifier", max_length=255, null=True, unique=True, default=None, blank=True)