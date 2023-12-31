from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericRelation

from simple_history.models import HistoricalRecords

from approval.models import RecordToBeApproved
from common.models import SaveWithoutHistoricalRecord

from django.conf import settings
LAB_ABBREVIATION_FOR_FILES = getattr(settings, 'LAB_ABBREVIATION_FOR_FILES', '')
OVE_URL = getattr(settings, 'OVE_URL', '')


class Oligo (models.Model, SaveWithoutHistoricalRecord):
    
    name = models.CharField("name", max_length=255, unique=True, blank=False)
    sequence = models.CharField("sequence", max_length=255, unique=True, blank=False)
    length = models.SmallIntegerField("length", null=True)
    us_e = models.CharField("use", max_length=255, blank=True)
    gene = models.CharField("gene", max_length=255, blank=True)
    restriction_site = models.CharField("restriction sites", max_length=255, blank=True)
    description = models.TextField("description", blank=True)
    comment = models.CharField("comments", max_length=255, blank=True)
    
    created_date_time = models.DateTimeField("created", auto_now_add=True)
    created_approval_by_pi = models.BooleanField("record creation approval", default=False)
    last_changed_date_time = models.DateTimeField("last changed", auto_now=True)
    last_changed_approval_by_pi = models.BooleanField("record change approval", default=None, null=True)
    approval_by_pi_date_time = models.DateTimeField(null=True, default=None)
    approval = GenericRelation(RecordToBeApproved)
    created_by = models.ForeignKey(User, related_name='oligo_createdby_user', on_delete=models.PROTECT)
    history = HistoricalRecords()
    
    def __str__(self):
       return "{} - {}".format(self.id, self.name)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        
        # Automatically capitalize the sequence of an oligo and remove all white spaces
        # from it. Also set its lenght
        upper_sequence = self.sequence.upper()
        self.sequence = "".join(upper_sequence.split())
        self.length = len(self.sequence)
        
        super(Oligo, self).save(force_insert, force_update, using, update_fields)
