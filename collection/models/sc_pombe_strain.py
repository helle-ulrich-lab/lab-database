from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.contrib.auth.models import User
from django.forms import ValidationError
from django.contrib.contenttypes.fields import GenericRelation

from datetime import timedelta
import random

from simple_history.models import HistoricalRecords

from approval.models import RecordToBeApproved
from common.models import SaveWithoutHistoricalRecord
from formz.models import FormZBaseElement
from formz.models import FormZProject
from formz.models import GenTechMethod
from common.models import DocFileMixin


class ScPombeStrain (models.Model, SaveWithoutHistoricalRecord):
    
    box_number = models.SmallIntegerField("box number", blank=False)
    parent_1 = models.ForeignKey('self', verbose_name='Parent 1', on_delete=models.PROTECT, related_name='pombe_parent_1', help_text='Main parental strain', blank=True, null=True)
    parent_2 = models.ForeignKey('self', verbose_name='Parent 2', on_delete=models.PROTECT, related_name='pombe_parent_2', help_text='Only for crosses', blank=True, null=True)
    parental_strain = models.CharField("parental strains", max_length=255, blank=True)
    mating_type = models.CharField("mating type", max_length=20, blank=True)
    auxotrophic_marker = models.CharField("auxotrophic markers", max_length=255, blank=True)
    name = models.TextField("genotype", blank=False)
    phenotype = models.CharField("phenotype", max_length=255, blank=True)
    received_from = models.CharField("received from", max_length=255, blank=True)
    comment = models.CharField("comments", max_length=300, blank=True)

    integrated_plasmids = models.ManyToManyField('Plasmid', related_name='pombe_integrated_plasmids', blank=True)
    cassette_plasmids = models.ManyToManyField('Plasmid', related_name='pombe_cassette_plasmids', help_text='Tagging and knock out plasmids', blank=True)
    episomal_plasmids = models.ManyToManyField('Plasmid', related_name='pombe_episomal_plasmids', blank=True, through='ScPombeStrainEpisomalPlasmid')

    created_date_time = models.DateTimeField("created", auto_now_add=True)
    created_approval_by_pi = models.BooleanField("record creation approval", default=False)
    last_changed_date_time = models.DateTimeField("last changed", auto_now=True)
    last_changed_approval_by_pi = models.BooleanField("record change approval", default=None, null=True)
    approval_by_pi_date_time = models.DateTimeField(null=True, default=None)
    approval = GenericRelation(RecordToBeApproved)
    approval_user = models.ForeignKey(User, related_name='pombe_approval_user', on_delete=models.PROTECT, null=True)
    created_by = models.ForeignKey(User, related_name='pombe_createdby_user', on_delete=models.PROTECT)
    history = HistoricalRecords()

    formz_projects = models.ManyToManyField(FormZProject, verbose_name='formZ projects', related_name='pombe_formz_project', blank=False)
    formz_risk_group = models.PositiveSmallIntegerField('risk group', choices=((1,1), (2,2)), blank=False, null=True)
    formz_gentech_methods = models.ManyToManyField(GenTechMethod, verbose_name='genTech methods', related_name='pombe_gentech_method', blank=True,
                                                    help_text='The methods used to create the strain')
    formz_elements = models.ManyToManyField(FormZBaseElement, verbose_name ='elements', related_name='pombe_formz_element', 
                                            help_text='Use only when an element is not present in the chosen plasmid(s), if any. '
                                                      'Searching against the aliases of an element is case-sensitive. '
                                                      '<a href="/formz/formzbaseelement/" target="_blank">View all/Change</a>', blank=True)
    destroyed_date = models.DateField("destroyed", blank=True, null=True)

    # Fields to keep a record of M2M field values (only IDs!) in the main strain record
    history_integrated_plasmids = ArrayField(models.PositiveIntegerField(), verbose_name="integrated plasmid", blank=True, null=True, default=list)
    history_cassette_plasmids =ArrayField(models.PositiveIntegerField(), verbose_name="cassette plasmids", blank=True, null=True, default=list)
    history_episomal_plasmids = ArrayField(models.PositiveIntegerField(), verbose_name="episomal plasmids", blank=True, null=True, default=list)
    history_all_plasmids_in_stocked_strain = ArrayField(models.PositiveIntegerField(), verbose_name="all plasmids in stocked strain", blank=True, null=True, default=list) # Integrated, cassete and episomal (only if present in -80 stock)
    history_formz_projects =ArrayField(models.PositiveIntegerField(), verbose_name="formZ projects", blank=True, null=True, default=list)
    history_formz_gentech_methods = ArrayField(models.PositiveIntegerField(), verbose_name="genTech methods", blank=True, null=True, default=list)
    history_formz_elements = ArrayField(models.PositiveIntegerField(), verbose_name="formz elements", blank=True, null=True, default=list)
    history_documents = ArrayField(models.PositiveIntegerField(), verbose_name="documents", blank=True, null=True, default=list)

    _model_abbreviation = 'sp'

    class Meta:
        verbose_name = 'strain - Sc. pombe'
        verbose_name_plural = 'strains - Sc. pombe'
    
    def __str__(self):
        return "{} - {}".format(self.id, self.get_genotype())

    def get_all_instock_plasmids(self):
        """Returns all plasmids present in the stocked organism"""

        all_plasmids = (self.integrated_plasmids.all() | \
            self.cassette_plasmids.all() | \
            self.episomal_plasmids.all()).distinct().order_by('id')
        return all_plasmids

    def get_all_transient_episomal_plasmids(self):
        """Returns all transiently transformed episomal plasmids"""

        all_plasmids = self.scpombestrainepisomalplasmid_set.filter(present_in_stocked_strain=False).distinct().order_by('plasmid__id')
        return all_plasmids

    def get_all_maps(self):
        """Returns all plasmids"""
        return (self.integrated_plasmids.all() | self.episomal_plasmids.all() | self.cassette_plasmids.all()).distinct().exclude(map='').order_by('id')

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
    
    def get_genotype(self):

        """Returns the full genotype of a pombe strain"""

        return ' '.join([e for e in [self.auxotrophic_marker, self.name] if e])


class ScPombeStrainEpisomalPlasmid (models.Model):

    _inline_foreignkey_fieldname = 'scpombe_strain'

    scpombe_strain = models.ForeignKey(ScPombeStrain, on_delete=models.PROTECT)
    plasmid = models.ForeignKey('Plasmid', verbose_name = 'Plasmid', on_delete=models.PROTECT)
    present_in_stocked_strain = models.BooleanField("present in -80° C stock?", default = False)
    formz_projects = models.ManyToManyField(FormZProject, related_name='pombe_episomal_plasmid_projects', blank= True)
    created_date = models.DateField('created', blank= True, null=True)
    destroyed_date = models.DateField('destroyed', blank= True, null=True)

    def clean(self):
    
        errors = []

        # Check that a transiently transfected plasmid has a created date
        if not self.present_in_stocked_strain and not self.created_date:
                errors.append(ValidationError('Transiently tranformed episomal plasmids must have a created date'))

        if len(errors) > 0:
            raise ValidationError(errors)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        
        # If destroyed date not present and plasmid not in stocked strain, automatically set destroyed date
        if self.present_in_stocked_strain:
            self.created_date = None
            self.destroyed_date = None
        else:
            if not self.destroyed_date and self.created_date:
                self.destroyed_date = self.created_date + timedelta(days=random.randint(7,28))
        
        super(ScPombeStrainEpisomalPlasmid, self).save(force_insert, force_update, using, update_fields)

    def is_highlighted(self):
        return self.present_in_stocked_strain

class ScPombeStrainDoc(DocFileMixin):

    _inline_foreignkey_fieldname = 'scpombe_strain'

    scpombe_strain = models.ForeignKey(ScPombeStrain, on_delete=models.PROTECT)

    _mixin_props = {'destination_dir': 'collection/scpombestraindoc/',
                    'file_prefix': 'spDoc',
                    'parent_field_name': 'scpombe_strain'}

    class Meta:
        verbose_name = 'sc. pombe strain document'