from django.db import models
from django.contrib.auth.models import User
from django.forms import ValidationError

from simple_history.models import HistoricalRecords

from common.models import SaveWithoutHistoricalRecord


class Inhibitor (models.Model, SaveWithoutHistoricalRecord):

    name = models.CharField("name", max_length = 255, blank=False)
    other_names = models.CharField("other names", max_length = 255, blank=False)
    target = models.CharField("target", max_length = 255, blank=True)
    received_from = models.CharField("received from", max_length = 255, blank=True)
    catalogue_number = models.CharField("catalogue number", max_length = 255, blank=True)
    l_ocation = models.CharField("location", max_length = 255, blank=True)
    ic50 = models.CharField("IC50", max_length = 255, blank=True)
    amount = models.CharField("amount", max_length = 255, blank=True)
    stock_solution = models.CharField("stock solution", max_length = 255, blank=True)
    description_comment = models.TextField("description/comments", blank=True)
    info_sheet = models.FileField("info sheet", help_text = 'only .pdf files, max. 2 MB', upload_to="collection/inhibitor/", blank=True, null=True)

    created_date_time = models.DateTimeField("created", auto_now_add=True)
    last_changed_date_time = models.DateTimeField("last changed", auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    history = HistoricalRecords()

    def clean(self):

        errors = []
        file_size_limit = 2 * 1024 * 1024
        
        if self.info_sheet:
            
            # Check if file is bigger than 2 MB
            if self.info_sheet.size > file_size_limit:
                errors.append(ValidationError('File too large. Size cannot exceed 2 MB.'))
            
            # Check if file's extension is '.pdf'
            try:
                info_sheet_ext = self.info_sheet.name.split('.')[-1].lower()
            except:
                info_sheet_ext = None
            if info_sheet_ext == None or info_sheet_ext != 'pdf':
                errors.append(ValidationError('Invalid file format. Please select a valid .pdf file'))

        if len(errors) > 0:
            raise ValidationError(errors)
    
    class Meta:
        verbose_name = 'inhibitor'
        verbose_name_plural = 'inhibitors'
    
    def __str__(self):
        return str(self.id)