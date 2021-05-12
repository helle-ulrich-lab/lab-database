#################################################
#    DJANGO 'CORE' FUNCTIONALITIES IMPORTS      #
#################################################

from django.db import models
from django.contrib.auth.models import User
from django.utils.encoding import force_text
from django.contrib.contenttypes.fields import GenericRelation
from django.forms import ValidationError

#################################################
#        ADDED FUNCTIONALITIES IMPORTS          #
#################################################

from simple_history.models import HistoricalRecords
import os
import time
from record_approval.models import RecordToBeApproved
from django_project.private_settings import LAB_ABBREVIATION_FOR_FILES

#################################################
#                CUSTOM CLASSES                 #
#################################################

class SaveWithoutHistoricalRecord():

    def save_without_historical_record(self, *args, **kwargs):
        """Allows inheritance of a method to save an object without
        saving a historical record as described in  
        https://django-simple-history.readthedocs.io/en/2.7.2/querying_history.html?highlight=save_without_historical_record"""

        self.skip_history_when_saving = True
        try:
            ret = self.save(*args, **kwargs)
        finally:
            del self.skip_history_when_saving
        return ret

#################################################
#                  VALIDATORS                   #
#################################################

def validate_absence_airquotes(value):
    if "'" in value or '"' in value:
        raise ValidationError('Single {} or double {} air-quotes are not allowed in this field'.format("'", '"'))

#################################################
#            ORDER COST UNIT MODEL              #
#################################################

class CostUnit(models.Model):
    
    name = models.CharField("Name", max_length=255, unique=True, blank=False)
    description = models.CharField("Description", max_length=255, unique=True, blank=False)
    status = models.BooleanField("deactivate?", help_text="Check it, if you want to HIDE this cost unit from the 'Add new order' form", default=False)
    
    class Meta:
        verbose_name = 'cost unit'
        ordering = ["name",]
    
    def __str__(self):
        return "{} - {}".format(self.name, self.description)

    def save(self, force_insert=False, force_update=False):
        
        # Force name to lower case
        self.name = self.name.lower()
        super(CostUnit, self).save(force_insert, force_update)

#################################################
#             ORDER LOCATION MODEL              #
#################################################

class Location(models.Model):
    
    name = models.CharField("name", max_length=255, unique=True, blank=False)
    status = models.BooleanField("deactivate?", help_text="Check it, if you want to HIDE this location from the 'Add new order' form ", default=False)
    
    class Meta:
        ordering = ["name",]

    def __str__(self):
        return self.name
    
    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        
        # Force name to lower case
        self.name = self.name.lower()
        
        super(Location, self).save(force_insert, force_update, using, update_fields)

#################################################
#               MSDS FORD MODEL                 #
#################################################

class MsdsForm(models.Model):
    
    name = models.FileField("file name", help_text = 'max. 2 MB', upload_to="order_management/msdsform/", unique=True, blank=False)
    
    created_date_time = models.DateTimeField("created", auto_now_add=True, null=True)
    last_changed_date_time = models.DateTimeField("last changed", auto_now=True, null=True)

    class Meta:
        verbose_name = 'MSDS form'
    
    def __str__(self):
        return os.path.splitext(os.path.basename(str(self.name)))[0]

    def clean(self):

        errors = []
        file_size_limit = 2 * 1024 * 1024
        
        if self.name:
            
            # Check if file is bigger than 2 MB
            if self.name.size > file_size_limit:
                errors.append(ValidationError('File too large. Size cannot exceed 2 MB.'))
            
            # Check if file has extension
            try:
                file_ext = self.name.name.split('.')[-1].lower()
            except:
                errors.append(ValidationError('Invalid file format. File does not have an extension'))

        if len(errors) > 0:
            raise ValidationError(errors)

#################################################
#                 ORDER MODEL                   #
#################################################

ORDER_STATUS_CHOICES = (('submitted', 'submitted'), 
('open', 'open'),
('arranged', 'arranged'), 
('delivered', 'delivered'),
('cancelled', 'cancelled'),
('used up', 'used up'))

HAZARD_LEVEL_PREGNANCY_CHOICES = (('none', 'none'), 
('yellow', 'yellow'), 
('red', 'red'))

class Order(models.Model, SaveWithoutHistoricalRecord):
    
    supplier = models.CharField("supplier", max_length=255, blank=False, validators=[validate_absence_airquotes])
    supplier_part_no = models.CharField("supplier Part-No", max_length=255, blank=False, validators=[validate_absence_airquotes], help_text='To see suggestions, type three characters or more')
    internal_order_no = models.CharField("internal order number", max_length=255, blank=True)
    part_description = models.CharField("part description", max_length=255, blank=False, validators=[validate_absence_airquotes], help_text='To see suggestions, type three characters or more')
    quantity = models.CharField("quantity", max_length=255, blank=False, validators=[validate_absence_airquotes])
    price = models.CharField("price", max_length=255, blank=True, validators=[validate_absence_airquotes])
    cost_unit = models.ForeignKey(CostUnit, on_delete=models.PROTECT, default=1, null=True, blank=False)
    status = models.CharField("status", max_length=255, choices=ORDER_STATUS_CHOICES, default="submitted", blank=False)
    urgent = models.BooleanField("is this an urgent order?", default=False)
    delivery_alert = models.BooleanField("delivery notification?", default=False)
    sent_email = models.BooleanField(default=False, null=True)
    location = models.ForeignKey(Location, on_delete=models.PROTECT, null=True, blank=False)
    comment =  models.TextField("comments", blank=True)
    order_manager_created_date_time = models.DateTimeField("created in OrderManager", blank=True, null=True)
    delivered_date = models.DateField("delivered", blank=True, default=None, null=True)
    url = models.URLField("URL", max_length=400, blank=True)
    cas_number = models.CharField("CAS number", max_length=255, blank=True, validators=[validate_absence_airquotes])
    ghs_pictogram_old = models.CharField("GHS pictogram", max_length=255, blank=True, validators=[validate_absence_airquotes])
    ghs_symbols = models.ManyToManyField('GhsSymbol', verbose_name ='GHS symbols', related_name='order_ghs_symbols', blank=True)
    signal_words = models.ManyToManyField('SignalWord', verbose_name ='signal words', related_name='order_signal_words', blank=True)
    history_ghs_symbols = models.TextField("GHS symbols", blank=True)
    history_signal_words = models.TextField("signal words", blank=True)
    ghs_symbols_autocomplete = models.TextField(default='')
    signal_words_autocomplete = models.TextField(default='')
    msds_form = models.ForeignKey(MsdsForm, on_delete=models.PROTECT, verbose_name='MSDS form', blank=True, null=True)
    hazard_level_pregnancy = models.CharField("Hazard level for pregnancy", max_length=255, choices=HAZARD_LEVEL_PREGNANCY_CHOICES, default='none', blank=True)
    
    created_date_time = models.DateTimeField("created", auto_now_add=True, null=True)
    last_changed_date_time = models.DateTimeField("last changed", auto_now=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    created_approval_by_pi = models.BooleanField(default=False, null=True)
    approval = GenericRelation(RecordToBeApproved)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'order'
    
    def __str__(self):
         return "{} - {}".format(self.id, self.part_description)
    
    def save_without_historical_record(self, *args, **kwargs):
        """Allows inheritance of a method to save an object without
        saving a historical record as described in  
        https://django-simple-history.readthedocs.io/en/2.7.2/querying_history.html?highlight=save_without_historical_record"""

        self.skip_history_when_saving = True
        try:
            ret = self.save(*args, **kwargs)
        finally:
            del self.skip_history_when_saving
        return ret
    
    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        
        # Remove trailing whitespace and internal new-line characters from specific fields
        self.supplier = self.supplier.strip().replace('\n'," ")
        self.supplier_part_no = self.supplier_part_no.strip().replace('\n'," ")
        self.part_description = self.part_description.strip().replace('\n'," ")
        self.quantity = self.quantity.strip().replace('\n'," ")
        self.price = self.price.strip().replace('\n'," ")
        self.cas_number = self.cas_number.strip().replace('\n'," ")
        self.ghs_pictogram_old = self.ghs_pictogram_old.strip().replace('\n'," ")
        
        super(Order, self).save(force_insert, force_update, using, update_fields)

#################################################
#           ORDER EXTRA DOC MODEL               #
#################################################

class OrderExtraDoc(models.Model):
    
    name = models.FileField("file name", help_text = 'max. 2 MB', upload_to="temp/", blank=False)
    description = models.CharField("description", max_length=255, blank=False)
    order = models.ForeignKey(Order, on_delete=models.PROTECT, null=True)
    
    created_date_time = models.DateTimeField("created", auto_now_add=True)
    last_changed_date_time = models.DateTimeField("last changed", auto_now=True)

    class Meta:
        verbose_name = 'order extra document'
    
    def __str__(self):
         return str(self.id)

    RENAME_FILES = {
        'name': 
        {'dest': 'order_management/orderextradoc/', 
        'keep_ext': True}
        }

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        
        # Rename a file of any given name to  ordocXX_date-uploaded_time-uploaded.ext,
        # after the corresponding entry has been created

        rename_files = getattr(self, 'RENAME_FILES', None)
        
        if rename_files:
            
            super(OrderExtraDoc, self).save(force_insert, force_update, using, update_fields)
            force_insert, force_update = False, True
            
            for field_name, options in rename_files.items():
                field = getattr(self, field_name)
                
                if field:
                    
                    # Create new file name
                    file_name = force_text(field)
                    name, ext = os.path.splitext(file_name)
                    ext = ext.lower()
                    keep_ext = options.get('keep_ext', True)
                    final_dest = options['dest']
                    
                    if callable(final_dest):
                        final_name = final_dest(self, file_name)
                    else:
                        final_name = os.path.join(final_dest, "ordoc" + LAB_ABBREVIATION_FOR_FILES + str(self.order.id) + "_" + time.strftime("%Y%m%d") + "_" + time.strftime("%H%M%S") + "_" + str(self.id))
                        if keep_ext:
                            final_name += ext
                    
                    # Essentially, rename file
                    if file_name != final_name:
                        field.storage.delete(final_name)
                        field.storage.save(final_name, field)
                        field.close()
                        field.storage.delete(file_name)
                        setattr(self, field_name, final_name)
        
        super(OrderExtraDoc, self).save(force_insert, force_update, using, update_fields)

    def clean(self):

        errors = []
        file_size_limit = 2 * 1024 * 1024
        
        if self.name:
            
            # Check if file is bigger than 2 MB
            if self.name.size > file_size_limit:
                errors.append(ValidationError('File too large. Size cannot exceed 2 MB.'))
            
            # Check if file has extension
            try:
                file_ext = self.name.name.split('.')[-1].lower()
            except:
                errors.append(ValidationError('Invalid file format. File does not have an extension'))

        if len(errors) > 0:
            raise ValidationError(errors)

class GhsSymbol(models.Model):
    code = models.CharField("code", max_length=10, unique=True, blank=False)
    pictogram = models.ImageField("pictogram", upload_to="temp/", help_text="only .png images, max. 2 MB", blank=False)
    description = models.CharField("description", max_length=255, blank=False)

    class Meta:
        verbose_name = 'GHS symbol'
    
    def __str__(self):
         return "{} - {}".format(self.code, self.description)

    RENAME_FILES = {
        'pictogram': 
        {'dest': 'order_management/ghssymbol', 
        'keep_ext': True}
        }

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        
        # Rename a file of any given name to  ghs_{id}_{code}.png,
        # after the corresponding entry has been created

        self.code = self.code.strip().upper()
        self.description = self.description.strip()

        rename_files = getattr(self, 'RENAME_FILES', None)
        
        if rename_files:
            
            super(GhsSymbol, self).save(force_insert, force_update, using, update_fields)
            force_insert, force_update = False, True
            
            for field_name, options in rename_files.items():
                field = getattr(self, field_name)
                
                if field:
                    
                    # Create new file name
                    file_name = force_text(field)
                    name, ext = os.path.splitext(file_name)
                    ext = ext.lower()
                    keep_ext = options.get('keep_ext', True)
                    final_dest = options['dest']
                    
                    if callable(final_dest):
                        final_name = final_dest(self, file_name)
                    else:
                        final_name = os.path.join(final_dest, "ghs_" + str(self.id) + "_" + str(self.code))
                        if keep_ext:
                            final_name += ext
                    
                    # Essentially, rename file
                    if file_name != final_name:
                        field.storage.delete(final_name)
                        field.storage.save(final_name, field)
                        field.close()
                        field.storage.delete(file_name)
                        setattr(self, field_name, final_name)
        
        super(GhsSymbol, self).save(force_insert, force_update, using, update_fields)

    def clean(self):

        errors = []
        file_size_limit = 2 * 1024 * 1024
        
        if self.pictogram:
            
            # Check if file is bigger than 2 MB
            if self.pictogram.size > file_size_limit:
                errors.append(ValidationError('File too large. Size cannot exceed 2 MB.'))
            
            # Check if file has extension
            try:
                img_ext = self.pictogram.name.split('.')[-1].lower()
            except:
                img_ext = None
            if img_ext == None or img_ext != 'png':
                errors.append(ValidationError('Invalid file format. Please select a valid .png file'))
            
        if len(errors) > 0:
            raise ValidationError(errors)

class SignalWord(models.Model):

    signal_word = models.CharField("signal word", max_length=255, unique=True, blank=False)

    class Meta:
        verbose_name = 'signal word'
    
    def __str__(self):
         return self.signal_word

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):

        self.signal_word = self.signal_word.strip()
        
        super(SignalWord, self).save(force_insert, force_update, using, update_fields)
