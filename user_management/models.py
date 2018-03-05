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
    user = models.OneToOneField(User)
    personal_order_list_url = models.URLField("Personal order list URL", max_length=255, blank=False, unique=True)
    abbreviation_code = models.CharField("User code (Max. 4 letters)", max_length=4, blank=False, unique=True)
    
    def save(self, force_insert=False, force_update=False):
        '''Automatically format personal order list url to lowercase and
        abbreviation code to upper case'''

        self.personal_order_list_url = self.personal_order_list_url.lower()
        self.abbreviation_code = self.abbreviation_code.upper()
        super(LabUser, self).save(force_insert, force_update)
