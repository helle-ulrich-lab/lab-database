# -*- coding: utf-8 -*-

from __future__ import unicode_literals

#################################################
#    DJANGO 'CORE' FUNCTIONALITIES IMPORTS      #
#################################################

from django.db import models
from django.contrib.auth.models import User
from django.utils.encoding import force_text

#################################################
#        ADDED FUNCTIONALITIES IMPORTS          #
#################################################

from simple_history.models import HistoricalRecords

import os
import time

#################################################
#            ORDER COST UNIT MODEL              #
#################################################

class CostUnit(models.Model):
    name = models.CharField("Name", max_length = 255, unique = True, blank=False)
    description = models.CharField("Description", max_length = 255, unique = True, blank=False)
    status = models.BooleanField("Deactivate?", default = False)
    
    class Meta:
        verbose_name = 'cost unit'
        ordering = ["name",]
    
    def __str__(self):
        return "{} - {}".format(self.name, self.description)

    def save(self, force_insert=False, force_update=False):
        
        self.name = self.name.lower()

        super(CostUnit, self).save(force_insert, force_update)

#################################################
#             ORDER LOCATION MODEL              #
#################################################

class Location(models.Model):
    name = models.CharField("Name", max_length = 255, unique = True, blank=False)
    status = models.BooleanField("Deactivate?", default = False)
    
    class Meta:
        ordering = ["name",]

    def __str__(self):
        return self.name
    
    def save(self, force_insert=False, force_update=False):
        
        self.name = self.name.lower()

        super(Location, self).save(force_insert, force_update)

#################################################
#               MSDS FORD MODEL                 #
#################################################

class MsdsForm(models.Model):
    name = models.FileField("File name", upload_to="order_management/msdsform/", blank=False)
    
    created_date_time = models.DateTimeField("Created", auto_now_add=True)
    last_changed_date_time = models.DateTimeField("Last Changed", auto_now=True)

    class Meta:
        verbose_name = 'MSDS form'
    
    def __str__(self):
         return os.path.splitext(os.path.basename(str(self.name)))[0]

    def clean(self):
        """Check if file is bigger than 2 MB"""

        errors = []
        
        limit = 2 * 1024 * 1024
        if self.name:
            if self.name.size > limit:
                errors.append(ValidationError('File too large. Size cannot exceed 2 MB.'))
            try:
                file_ext = self.name.name.split('.')[-1].lower()
            except:
                errors.append(ValidationError('Invalid file format. File does not have an extension'))

        if len(errors) > 0:
            raise ValidationError(errors)

#################################################
#                 ORDER MODEL                   #
#################################################

status_choices = (('submitted', 'submitted'), 
('open', 'open'),
('arranged', 'arranged'), 
('delivered', 'delivered'),
('cancelled', 'cancelled'),
('used up', 'used up'))

class Order(models.Model):
    supplier = models.CharField("Supplier", max_length = 255, blank=False)
    supplier_part_no = models.CharField("Supplier Part-No", max_length = 255, blank=False)
    internal_order_no = models.CharField("Internal order number", max_length = 255, blank=True)
    part_description = models.CharField("Part Description", max_length = 255, blank=False)
    quantity = models.CharField("Quantity", max_length = 255, blank=False)
    price = models.CharField("Price", max_length = 255, blank=True)
    cost_unit = models.ForeignKey(CostUnit, on_delete=models.PROTECT, default=1)
    status = models.CharField("Status", max_length = 255, choices= status_choices, default="submitted", blank = False)
    urgent = models.BooleanField("Is this an urgent order?", default = False)
    delivery_alert = models.BooleanField("Delivery notification?", default = False)
    sent_email = models.BooleanField(default=False)
    location = models.ForeignKey(Location, on_delete=models.PROTECT, null = True)
    comment =  models.TextField("Comments", blank=True)
    order_manager_created_date_time = models.DateTimeField("Created in OrderManager", blank = True, null = True)
    delivered_date = models.DateField("Delivered", blank = True, null = True, default = None)
    url = models.URLField("URL", max_length = 400, blank = True)
    cas_number = models.CharField("CAS number", max_length = 255, blank=True)
    ghs_pictogram = models.CharField("GHS pictogram", max_length = 255, blank=True)
    msds_form = models.ForeignKey(MsdsForm, on_delete=models.PROTECT, blank=True, null = True)
    
    created_date_time = models.DateTimeField("Created", auto_now_add=True)
    last_changed_date_time = models.DateTimeField("Last Changed", auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    created_approval_by_pi = models.BooleanField(default = False)
    history = HistoricalRecords()

    class Meta:
        '''Set a custom name to be used throughout the admin pages'''
        
        verbose_name = 'order'
    
    def __str__(self):
         return str(self.id)
    
    def save_without_historical_record(self, *args, **kwargs):
        self.skip_history_when_saving = True
        try:
            ret = self.save(*args, **kwargs)
        finally:
            del self.skip_history_when_saving
        return ret
    
    def save(self, force_insert=False, force_update=False):
        self.supplier = self.supplier.strip().replace("'","").replace('\n'," ").replace('#'," ")
        self.supplier_part_no = self.supplier_part_no.strip().replace("'","").replace('\n'," ").replace('#'," ")
        self.part_description = self.part_description.strip().replace("'","").replace('\n'," ").replace('#'," ")
        self.quantity = self.quantity.strip().replace("'","").replace('\n'," ").replace('#'," ")
        self.price = self.price.strip().replace("'","").replace('\n'," ").replace('#'," ")
        self.cas_number = self.cas_number.strip().replace("'","").replace('\n'," ").replace('#'," ")
        self.ghs_pictogram = self.ghs_pictogram.strip().replace("'","").replace('\n'," ").replace('#'," ")
        super(Order, self).save(force_insert, force_update)

#################################################
#           ORDER EXTRA DOC MODEL               #
#################################################

class OrderExtraDoc(models.Model):
    name = models.FileField("File name", upload_to="temp/", blank=False)
    description = models.CharField("Description", max_length = 255, blank=False)
    order = models.ForeignKey(Order, on_delete=models.PROTECT)
    
    created_date_time = models.DateTimeField("Created", auto_now_add=True)
    last_changed_date_time = models.DateTimeField("Last Changed", auto_now=True)

    class Meta:
        verbose_name = 'order extra document'
    
    def __str__(self):
         return str(self.id)

    RENAME_FILES = {
        'name': 
        {'dest': 'order_management/orderextradoc/', 
        'keep_ext': True}
        }

    def save(self, force_insert=False, force_update=False):
        '''Override default save method to rename a file 
        of any given name to ordocHU_date-uploaded_time-uploaded.yyy,
        after the corresponding entry has been created'''
        
        rename_files = getattr(self, 'RENAME_FILES', None)
        if rename_files:
            super(OrderExtraDoc, self).save(force_insert, force_update)
            force_insert, force_update = False, True
            for field_name, options in rename_files.items():
                field = getattr(self, field_name)
                if field:
                    file_name = force_text(field)
                    name, ext = os.path.splitext(file_name)
                    ext = ext.lower()
                    keep_ext = options.get('keep_ext', True)
                    final_dest = options['dest']
                    if callable(final_dest):
                        final_name = final_dest(self, file_name)
                    else:
                        final_name = os.path.join(final_dest, "ordocHU" + str(self.order.id) + "_" + time.strftime("%Y%m%d") + "_" + time.strftime("%H%M%S") + "_" + str(self.id))
                        if keep_ext:
                            final_name += ext
                    if file_name != final_name:
                        field.storage.delete(final_name)
                        field.storage.save(final_name, field)
                        field.close()
                        field.storage.delete(file_name)
                        setattr(self, field_name, final_name)
        super(OrderExtraDoc, self).save(force_insert, force_update)

    def clean(self):
        """Check if file is bigger than 2 MB"""

        errors = []
        
        limit = 2 * 1024 * 1024
        if self.name:
            if self.name.size > limit:
                errors.append(ValidationError('File too large. Size cannot exceed 2 MB.'))
            try:
                file_ext = self.name.name.split('.')[-1].lower()
            except:
                errors.append(ValidationError('Invalid file format. File does not have an extension'))

        if len(errors) > 0:
            raise ValidationError(errors)