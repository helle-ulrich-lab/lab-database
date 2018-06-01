# -*- coding: utf-8 -*-

from __future__ import unicode_literals

#################################################
#    DJANGO 'CORE' FUNCTIONALITIES IMPORTS      #
#################################################

from django.db import models
from django.contrib.auth.models import User

#################################################
#            ORDER COST UNIT MODEL              #
#################################################

class CostUnit(models.Model):
    name = models.CharField("Name", max_length = 255, blank=False)
    
    class Meta:
        verbose_name = 'cost unit'
    
    def __unicode__(self):
        return self.name

#################################################
#             ORDER LOCATION MODEL              #
#################################################

class Location(models.Model):
    name = models.CharField("Name", max_length = 255, blank=False)
    
    def __unicode__(self):
        return self.name

#################################################
#                 ORDER MODEL                   #
#################################################

class Order(models.Model):
    supplier = models.CharField("Supplier", max_length = 255, blank=False)
    supplier_part_no = models.CharField("Supplier Part-No", max_length = 255, blank=False)
    part_description = models.CharField("Part Description", max_length = 255, blank=False)
    quantity = models.CharField("Quantity", max_length = 255, blank=False)
    price = models.CharField("Price", max_length = 255, blank=True)
    cost_unit = models.ForeignKey(CostUnit, default=1)
    urgent = models.BooleanField("Is this an urgent order?")
    delivery_alert = models.BooleanField("Would you like to receive a delivery alert for this order?")
    location = models.ForeignKey(Location)
    comment =  models.TextField("Comments", blank=True)
    url = models.URLField("URL", max_length = 400, blank=True)
    
    created_date_time = models.DateTimeField("Created", auto_now_add=True)
    created_by = models.ForeignKey(User)