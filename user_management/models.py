# -*- coding: utf-8 -*-

from __future__ import unicode_literals

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