from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.contrib.auth.models import User
from django.forms import ValidationError
from django.contrib.contenttypes.fields import GenericRelation
from django.utils.encoding import force_str

from datetime import timedelta
import random
import os
import time

from simple_history.models import HistoricalRecords

from approval.models import RecordToBeApproved
from common.models import SaveWithoutHistoricalRecord
from formz.models import FormZBaseElement
from formz.models import FormZProject
from formz.models import GenTechMethod
from formz.models import Species
from formz.models import ZkbsCellLine
from common.models import DocFileMixin

from django.conf import settings
LAB_ABBREVIATION_FOR_FILES = getattr(settings, 'LAB_ABBREVIATION_FOR_FILES', '')


class CellLine (models.Model, SaveWithoutHistoricalRecord):
    
    name = models.CharField("name", max_length=255, unique=True, blank=False)
    box_name = models.CharField("box", max_length=255, blank=False)
    alternative_name = models.CharField("alternative name", max_length=255, blank=True)
    parental_line_old = models.CharField("parental cell line", max_length=255, blank=False)
    parental_line = models.ForeignKey('self', on_delete=models.PROTECT, verbose_name = 'parental line', blank=True, null=True)
    organism = models.ForeignKey(Species, verbose_name = 'organism', on_delete=models.PROTECT, null=True, blank=True)
    cell_type_tissue = models.CharField("cell type/tissue", max_length=255, blank=True)
    culture_type = models.CharField("culture type", max_length=255, blank=True)
    growth_condition = models.CharField("growth conditions", max_length=255, blank=True)
    freezing_medium = models.CharField("freezing medium", max_length=255, blank=True)
    received_from = models.CharField("received from", max_length=255, blank=True)
    description_comment = models.TextField("description/comments", blank=True)
    s2_work = models.BooleanField("Used for S2 work?", default=False, help_text='Check, for example, for a cell line created by lentiviral trunsdunction')

    integrated_plasmids = models.ManyToManyField('Plasmid', related_name='cellline_integrated_plasmids', blank= True)
    episomal_plasmids = models.ManyToManyField('Plasmid', related_name='cellline_episomal_plasmids', blank=True, through='CellLineEpisomalPlasmid')
    
    created_date_time = models.DateTimeField("created", auto_now_add=True)
    created_approval_by_pi = models.BooleanField("record creation approval", default=False)
    last_changed_date_time = models.DateTimeField("last changed", auto_now=True)
    last_changed_approval_by_pi = models.BooleanField("record change approval", default=None, null=True)
    approval_by_pi_date_time = models.DateTimeField(null=True, default=None)
    approval = GenericRelation(RecordToBeApproved)
    approval_user = models.ForeignKey(User, related_name='cellline_approval_user', on_delete=models.PROTECT, null=True)
    created_by = models.ForeignKey(User, related_name='cellline_createdby_user', on_delete=models.PROTECT)
    history = HistoricalRecords()
    
    formz_projects = models.ManyToManyField(FormZProject, verbose_name='projects', related_name='cellline_zprojects', blank=False)
    formz_risk_group = models.PositiveSmallIntegerField('risk group', choices=((1,1), (2,2)), blank=False, null=True)
    zkbs_cell_line = models.ForeignKey(ZkbsCellLine, verbose_name = 'ZKBS database cell line', on_delete=models.PROTECT, null=True, blank=False,
                                       help_text='If not applicable, choose none. <a href="/formz/zkbscellline/" target="_blank">View all</a>')
    formz_gentech_methods = models.ManyToManyField(GenTechMethod, verbose_name='genTech methods', related_name='cellline_gentech_method', blank= True,
                                                    help_text='The methods used to create the cell line')
    formz_elements = models.ManyToManyField(FormZBaseElement, verbose_name ='elements', related_name='cellline_formz_element', 
                                            help_text='Use only when an element is not present in the chosen plasmid(s), if any. '
                                                      'Searching against the aliases of an element is case-sensitive. '
                                                      '<a href="/formz/formzbaseelement/" target="_blank">View all/Change</a>', blank=True)
    
    destroyed_date = models.DateField("destroyed", blank=True, null=True)

    # Fields to keep a record of M2M field values (only IDs!) in the main strain record
    history_integrated_plasmids = ArrayField(models.PositiveIntegerField(), verbose_name="integrated plasmid", blank=True, null=True)
    history_episomal_plasmids = ArrayField(models.PositiveIntegerField(), verbose_name="episomal plasmids", blank=True, null=True)
    history_formz_projects =ArrayField(models.PositiveIntegerField(), verbose_name="formZ projects", blank=True, null=True)
    history_formz_gentech_methods = ArrayField(models.PositiveIntegerField(), verbose_name="genTech methods", blank=True, null=True)
    history_formz_elements = ArrayField(models.PositiveIntegerField(), verbose_name="formz elements", blank=True, null=True)
    history_documents = ArrayField(models.PositiveIntegerField(), verbose_name="documents", blank=True, null=True)

    _model_abbreviation = 'cl'

    class Meta:
        verbose_name = 'cell line'
        verbose_name_plural = 'cell lines'
    
    def __str__(self):
        return "{} - {}".format(self.id, self.name)

    def get_all_instock_plasmids(self):
        """Returns all plasmids present in the stocked organism"""

        all_plasmids = self.integrated_plasmids.all().distinct().order_by('id')
        return all_plasmids

    def get_all_transient_episomal_plasmids(self):
        """Returns all transiently transformed episomal plasmids"""

        all_plasmids = self.celllineepisomalplasmid_set.filter(s2_work_episomal_plasmid=False).distinct().order_by('plasmid__id')
        return all_plasmids

    def get_all_plasmid_maps(self):
        """Returns all plasmids"""
        return (self.integrated_plasmids.all() | self.episomal_plasmids.all()).distinct().exclude(map='').order_by('id')

    def get_all_uncommon_formz_elements(self):
        """Returns all uncommon features in stocked organism"""

        elements = self.formz_elements.all()
        all_plasmids = self.get_all_instock_plasmids()
        for pl in all_plasmids:
            elements = elements | pl.formz_elements.all()
        elements = elements.distinct().filter(common_feature=False).order_by('name')
        return elements
    
    def get_all_common_formz_elements(self):
        """Returns all common features in stocked organism"""

        elements = self.formz_elements.all()
        all_plasmids = self.get_all_instock_plasmids()
        for pl in all_plasmids:
            elements = elements | pl.formz_elements.all()
        elements = elements.distinct().filter(common_feature=True).order_by('name')
        return elements


class CellLineEpisomalPlasmid (models.Model):
    
    cell_line = models.ForeignKey(CellLine, on_delete=models.PROTECT)
    plasmid = models.ForeignKey('Plasmid', verbose_name = 'Plasmid', on_delete=models.PROTECT)
    formz_projects = models.ManyToManyField(FormZProject, related_name='cellline_episomal_plasmid_projects', blank= True)
    s2_work_episomal_plasmid = models.BooleanField("Used for S2 work?", help_text="Check, for example, for lentiviral packaging plasmids", default=False)
    created_date = models.DateField('created', blank= False, null=True)
    destroyed_date = models.DateField('destroyed', blank= True, null=True)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        
        # If destroyed date not present and plasmid not in stocked strain, automatically set destroyed date
        if not self.destroyed_date and self.created_date:
            if self.s2_work_episomal_plasmid:
                self.destroyed_date = self.created_date + timedelta(days=2)
            else:
                self.destroyed_date = self.created_date + timedelta(days=random.randint(7,28))
        
        super(CellLineEpisomalPlasmid, self).save(force_insert, force_update, using, update_fields)
    
    def is_highlighted(self):
        return self.s2_work_episomal_plasmid

################################################
#               CELL LINE DOC                  #
################################################

CELL_LINE_DOC_TYPE_CHOICES = (
    ("virus", "Virus test"),
    ("mycoplasma", "Mycoplasma test"),
    ("fingerprint", "Fingerprinting"),
    ("other", "Other"))

class CellLineDoc(DocFileMixin):

    description = models.CharField("doc type", max_length=255, choices=CELL_LINE_DOC_TYPE_CHOICES, blank=False)
    date_of_test = models.DateField("date of test", blank=False, null=True)
    cell_line = models.ForeignKey(CellLine, on_delete=models.PROTECT)

    _mixin_props = {'destination_dir': 'collection/celllinedoc/',
                    'file_prefix': 'clDoc',
                    'parent_field_name': 'cell_line'}

    class Meta:
        verbose_name = 'cell line document'