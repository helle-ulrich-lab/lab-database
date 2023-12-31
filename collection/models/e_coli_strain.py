from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericRelation

from simple_history.models import HistoricalRecords

from approval.models import RecordToBeApproved
from common.models import SaveWithoutHistoricalRecord
from formz.models import FormZBaseElement
from formz.models import FormZProject


class EColiStrain (models.Model, SaveWithoutHistoricalRecord):
    
    name = models.CharField("name", max_length=255, blank=False)
    resistance = models.CharField("resistance", max_length=255, blank=True)
    genotype = models.TextField("genotype", blank=True)
    background = models.CharField("background", max_length=255, choices=(("B","B"), ("C","C"), ("K12","K12"), ("W","W")), blank=True)
    formz_risk_group = models.PositiveSmallIntegerField('risk group', choices=((1,1), (2,2)), blank=True, null=True)
    supplier = models.CharField("supplier", max_length=255)
    us_e = models.CharField("use", max_length=255, choices=(('Cloning', 'Cloning'),('Expression', 'Expression'),('Other', 'Other'),))
    purpose = models.TextField("purpose", blank=True)
    note =  models.TextField("note", max_length=255, blank=True)
    
    created_date_time = models.DateTimeField("created", auto_now_add=True)
    created_approval_by_pi = models.BooleanField("record creation approval", default=False)
    last_changed_date_time = models.DateTimeField("last changed", auto_now=True)
    last_changed_approval_by_pi = models.BooleanField("record change approval", default=None, null=True)
    approval_by_pi_date_time = models.DateTimeField(null=True, default=None)
    approval = GenericRelation(RecordToBeApproved)
    approval_user = models.ForeignKey(User, related_name='coli_approval_user', on_delete=models.PROTECT, null=True)
    created_by = models.ForeignKey(User, related_name='coli_createdby_user', on_delete=models.PROTECT)
    history = HistoricalRecords()

    formz_projects = models.ManyToManyField(FormZProject, verbose_name='formZ projects', related_name='coli_formz_project', blank=False)
    formz_elements = models.ManyToManyField(FormZBaseElement, verbose_name ='elements', related_name='coli_formz_element', blank=True, 
                                            help_text='Searching against the aliases of an element is case-sensitive. '
                                            '<a href="/formz/formzbaseelement/" target="_blank">View all/Change</a>')
    destroyed_date = models.DateField("destroyed", blank=True, null=True)

    history_formz_projects = ArrayField(models.PositiveIntegerField(), verbose_name="formZ projects", blank=True, null=True)
    history_formz_gentech_methods = ArrayField(models.PositiveIntegerField(), verbose_name="genTech methods", blank=True, null=True)
    history_formz_elements = ArrayField(models.PositiveIntegerField(), verbose_name="formz elements", blank=True, null=True)

    class Meta:
        verbose_name = 'strain - E. coli'
        verbose_name_plural = 'strains - E. coli'

    def get_all_instock_plasmids(self):
        """Returns all plasmids present in the stocked organism"""

        return None

    def get_all_transient_episomal_plasmids(self):
        """Returns all transiently transformed episomal plasmids"""

        return None

    def get_all_uncommon_formz_elements(self):
        """Returns all uncommon features in stocked organism"""

        elements = self.formz_elements.filter(common_feature=False).order_by('name')
        return elements
    
    def get_all_common_formz_elements(self):
        """Returns all common features in stocked organism"""

        elements = self.formz_elements.filter(common_feature=True).order_by('name')
        return elements
        
    def __str__(self):
       return "{} - {}".format(self.id, self.name)
