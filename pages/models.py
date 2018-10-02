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
from ckeditor_uploader.fields import RichTextUploadingField

#################################################
#               PROTOCOL MODEL                  #
#################################################

class Tag(models.Model):
    name = models.CharField("Tag", max_length = 50, unique=True)
    
    def __str__(self):
       return str(self.name)

class Protocol(models.Model):
    title = models.CharField("Title", max_length = 200, blank=False)
    content = RichTextUploadingField("Content", blank=False)
    tags = models.ManyToManyField(Tag, blank=True)
    
    created_date_time = models.DateTimeField("Created", auto_now_add=True)
    last_changed_date_time = models.DateTimeField("Last Changed", auto_now=True)
    created_by = models.ForeignKey(User)
    history = HistoricalRecords()
    
    def __str__(self):
       return str(self.id)

class Recipe(models.Model):
    title = models.CharField("Title", max_length = 200, blank=False)
    content = RichTextUploadingField("Content", blank=False)
    tags = models.ManyToManyField(Tag, blank=True)
    
    created_date_time = models.DateTimeField("Created", auto_now_add=True)
    last_changed_date_time = models.DateTimeField("Last Changed", auto_now=True)
    created_by = models.ForeignKey(User)
    history = HistoricalRecords()
    
    def __str__(self):
       return str(self.id)