from django.db import models
from django.contrib.auth.models import User
from django.forms import ValidationError
from django.contrib.postgres.fields import ArrayField
from django_better_admin_arrayfield.models.fields import ArrayField as BetterArrayField

from simple_history.models import HistoricalRecords
from common.models import SaveWithoutHistoricalRecord
from ordering.models import Order
from formz.models import Species
from common.models import DocFileMixin
from common.models import DownloadFileNameMixin

class SiRna (DownloadFileNameMixin, models.Model, SaveWithoutHistoricalRecord):

    name = models.CharField("name", max_length = 255, blank=False)
    sequence = models.CharField("sequence", max_length=50, help_text="Sense strand", blank=False)
    supplier = models.CharField("supplier", max_length=255, blank=False)
    supplier_part_no = models.CharField("supplier Part-No", max_length=255, blank=False)
    supplier_si_rna_id = models.CharField("supplier siRNA ID", max_length=255, blank=False)
    species = models.ForeignKey(Species, verbose_name = 'organism', on_delete=models.PROTECT, null=True, blank=False)
    target_genes = BetterArrayField(models.CharField(max_length=15), blank=False, null=True)
    locus_ids = BetterArrayField(models.CharField(max_length=15), blank=True, null=True)
    description_comment = models.TextField("description/comments", help_text='Include transfection conditions, etc. here', blank=True)
    info_sheet = models.FileField("info sheet", help_text = 'only .pdf files, max. 2 MB', upload_to="collection/sirna/", blank=True, null=True)
    orders = models.ManyToManyField(Order, verbose_name='orders', related_name='si_rna_order', blank=True)

    # Fields to keep a record of M2M field values (only IDs!) in the main strain record
    history_orders = ArrayField(models.PositiveIntegerField(), verbose_name="order", blank=True, null=True)

    created_date_time = models.DateTimeField("created", auto_now_add=True)
    last_changed_date_time = models.DateTimeField("last changed", auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    history = HistoricalRecords()

    history_documents = ArrayField(models.PositiveIntegerField(), verbose_name="documents", blank=True, null=True)

    _model_abbreviation = 'siRNA'
    _model_upload_to = 'collection/sirna/'


    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        
        # Remove all white spaces from sequence and set its length
        self.sequence = "".join(self.sequence.split())
        
        super(SiRna, self).save(force_insert, force_update, using, update_fields)

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
        verbose_name = 'siRNA'
        verbose_name_plural = 'siRNAs'
    
    def __str__(self):
        return str(self.id)

class SiRnaDoc(DocFileMixin):
    si_rna = models.ForeignKey(SiRna, on_delete=models.PROTECT)

    _mixin_props = {'destination_dir': 'collection/sirnadoc/',
                    'file_prefix': 'sirnaDoc',
                    'parent_field_name': 'si_rna'}

    class Meta:
        verbose_name = 'siRNA document'