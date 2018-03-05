# -*- coding: utf-8 -*-

from __future__ import unicode_literals

#################################################
#    DJANGO 'CORE' FUNCTIONALITIES IMPORTS      #
#################################################

from django.db import models
from django.contrib.auth.models import User

#################################################
#        ADDED FUNCTIONALITIES IMPORTS          #
#################################################

from simple_history.models import HistoricalRecords
from colorful.fields import RGBColorField

#################################################
#        LAB MANAGEMENT CATEGORY MODEL          #
#################################################

class Category(models.Model):
    name = models.CharField("Name", max_length = 255, blank=False)
    colour = RGBColorField(colors=['#f6e1f0', '#e1f0f6', '#f0f6e1', '#f6e7e1', '#e1e6f6', '#f6f2e1'], blank=False)
    
    created_date_time = models.DateTimeField("Created", auto_now_add=True)
    last_changed_date_time = models.DateTimeField("Last Changed", auto_now=True)
    created_by = models.ForeignKey(User)
    history = HistoricalRecords()
    
    def __unicode__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "categories"

#################################################
#           LAB MANAGEMENT URL MODEL            #
#################################################

class Url(models.Model):
    title = models.CharField("Title", max_length = 255, blank=False)
    url = models.URLField("URL", max_length = 400, blank=False)
    category = models.ForeignKey(Category)
    editable = models.BooleanField("Editable")

    created_date_time = models.DateTimeField("Created", auto_now_add=True)
    last_changed_date_time = models.DateTimeField("Last Changed", auto_now=True)
    created_by = models.ForeignKey(User)
    history = HistoricalRecords()