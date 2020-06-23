#################################################
#    DJANGO 'CORE' FUNCTIONALITIES IMPORTS      #
#################################################

from django.db import models
from django.contrib.auth.models import User
from django.forms import ValidationError
from django.utils.encoding import force_text
from django.contrib.contenttypes.fields import GenericRelation
from django.utils.safestring import mark_safe

from formz.models import ZkbsPlasmid
from formz.models import FormZBaseElement
from formz.models import FormZProject
from formz.models import ZkbsCellLine
from formz.models import GenTechMethod
from formz.models import Species

from record_approval.models import RecordToBeApproved
from django_project.private_settings import LAB_ABBREVIATION_FOR_FILES

#################################################
#        ADDED FUNCTIONALITIES IMPORTS          #
#################################################

from simple_history.models import HistoricalRecords
import os
import time
from datetime import timedelta, datetime
import random

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
#            SA. CEREVISIAE STRAIN              #
#################################################

CEREVISIAE_MATING_TYPE_CHOICES = (
    ('a','a'),
    ('alpha','alpha'),
    ('unknown','unknown'),
    ('a/a','a/a'),
    ('alpha/alpha','alpha/alpha'),
    ('a/alpha','a/alpha'),
    ('other', 'other')
)

class SaCerevisiaeStrain (models.Model, SaveWithoutHistoricalRecord):
    
    name = models.CharField("name", max_length=255, blank=False)
    relevant_genotype = models.CharField("relevant genotype", max_length=255, blank=False)
    mating_type = models.CharField("mating type", choices = CEREVISIAE_MATING_TYPE_CHOICES, max_length=20, blank=True)
    chromosomal_genotype = models.TextField("chromosomal genotype", blank=True)
    parent_1 = models.ForeignKey('self', verbose_name='Parent 1', on_delete=models.PROTECT, related_name='cerevisiae_parent_1', help_text='Main parental strain', blank=True, null=True)
    parent_2 = models.ForeignKey('self', verbose_name='Parent 2', on_delete=models.PROTECT, related_name='cerevisiae_parent_2', help_text='Only for crosses', blank=True, null=True)
    parental_strain = models.CharField("parental strain", help_text="Use only when 'Parent 1' does not apply", max_length=255, blank=True)
    construction = models.TextField("construction", blank=True)
    modification = models.CharField("modification", max_length=255, blank=True)
    
    integrated_plasmids = models.ManyToManyField('Plasmid', related_name='cerevisiae_integrated_plasmids', blank=True)
    cassette_plasmids = models.ManyToManyField('Plasmid', related_name='cerevisiae_cassette_plasmids', help_text='Tagging and knock out plasmids', blank=True)
    episomal_plasmids = models.ManyToManyField('Plasmid', related_name='cerevisiae_episomal_plasmids', blank=True, through='SaCerevisiaeStrainEpisomalPlasmid')
    plasmids = models.CharField("plasmids", max_length=255, help_text='Use only when the other plasmid fields do not apply', blank=True)
    
    selection = models.CharField("selection", max_length=255, blank=True)
    phenotype = models.CharField("phenotype", max_length=255, blank=True)
    background = models.CharField("background", max_length=255, blank=True)
    received_from = models.CharField("received from", max_length=255, blank=True)
    us_e = models.CharField("use", max_length=255, blank=True)
    note = models.CharField("note", max_length=255, blank=True)
    reference = models.CharField("reference", max_length=255, blank=True)
    
    created_date_time = models.DateTimeField("created", auto_now_add=True)
    created_approval_by_pi = models.BooleanField("record creation approval", default=False)
    last_changed_date_time = models.DateTimeField("last changed", auto_now=True)
    last_changed_approval_by_pi = models.NullBooleanField("record change approval", default=None)
    approval_by_pi_date_time = models.DateTimeField(null = True, default=None)
    approval = GenericRelation(RecordToBeApproved)
    approval_user = models.ForeignKey(User, related_name='cerevisiae_approval_user', on_delete=models.PROTECT, null=True)
    created_by = models.ForeignKey(User, related_name='cerevisiae_createdby_user', on_delete=models.PROTECT)
    history = HistoricalRecords()

    formz_projects = models.ManyToManyField(FormZProject, verbose_name='projects', related_name='cerevisiae_formz_project', blank=False)
    formz_risk_group = models.PositiveSmallIntegerField('risk group', choices=((1,1), (2,2)), blank=False, null=True)
    formz_gentech_methods = models.ManyToManyField(GenTechMethod, verbose_name='genTech methods', related_name='cerevisiae_gentech_method', blank= True,
                                                    help_text='The methods used to create the strain')
    formz_elements = models.ManyToManyField(FormZBaseElement, verbose_name ='elements', related_name='cerevisiae_formz_element', 
                                            help_text='Use only when an element is not present in the chosen plasmid(s), if any. '
                                            '<a href="/formz/formzbaseelement/" target="_blank">View all/Change</a>', blank=True)
    destroyed_date = models.DateField("destroyed", blank=True, null=True)

    # Fields to keep a record of M2M field values (only IDs!) in the main strain record
    history_integrated_plasmids = models.TextField("integrated plasmid", blank=True)
    history_cassette_plasmids = models.TextField("cassette plasmids", blank=True)
    history_episomal_plasmids = models.TextField("episomal plasmids", blank=True)
    history_all_plasmids_in_stocked_strain = models.TextField("all plasmids in stocked strain",blank=True) # Integrated, cassete and episomal (only if present in -80 stock)
    history_formz_projects = models.TextField("formZ projects", blank=True)
    history_formz_gentech_methods = models.TextField("genTech methods", blank=True)
    history_formz_elements = models.TextField("formz elements", blank=True)

    class Meta:
        verbose_name = 'strain - Sa. cerevisiae'
        verbose_name_plural = 'strains - Sa. cerevisiae'
    
    def __str__(self):
        return "{} - {}".format(self.id, self.name)

    def get_all_instock_plasmids(self):
        """Returns all plasmids present in the stocked organism"""

        all_plasmids = (self.integrated_plasmids.all() | \
            self.cassette_plasmids.all() | \
            self.episomal_plasmids.filter(sacerevisiaestrainepisomalplasmid__present_in_stocked_strain=True)).distinct().order_by('id')
        return all_plasmids

    def get_all_transient_episomal_plasmids(self):
        """Returns all transiently transformed episomal plasmids"""

        all_plasmids = self.sacerevisiaestrainepisomalplasmid_set.filter(present_in_stocked_strain=False).distinct().order_by('plasmid__id')
        return all_plasmids

    def get_all_plasmid_maps(self):
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

class SaCerevisiaeStrainEpisomalPlasmid (models.Model):
    
    sacerevisiae_strain = models.ForeignKey(SaCerevisiaeStrain, on_delete=models.PROTECT)
    plasmid = models.ForeignKey('Plasmid', verbose_name = 'Plasmid', on_delete=models.PROTECT)
    present_in_stocked_strain = models.BooleanField("present in -80° C stock?", help_text="Check, if the culture you stocked for the -80° C "
                                                    "collection contains an episomal plasmid. Leave unchecked, if you simply want to record that you have "
                                                    "transiently transformed this strain with an episomal plasmid", default=False)
    formz_projects = models.ManyToManyField(FormZProject, related_name='cerevisiae_episomal_plasmid_projects', blank= True)
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
        
        super(SaCerevisiaeStrainEpisomalPlasmid, self).save(force_insert, force_update, using, update_fields)

#################################################
#                    PLASMID                    #
#################################################

class Plasmid (models.Model, SaveWithoutHistoricalRecord):
    
    name = models.CharField("name", max_length=255, unique=True, blank=False)
    other_name = models.CharField("other name", max_length=255, blank=True)
    parent_vector = models.ForeignKey('self', verbose_name='parent vector', related_name = 'plasmid_parent_vector', on_delete=models.PROTECT, blank=True, null=True)
    old_parent_vector = models.CharField("orig. parent vector field", help_text='Use only when strictly necessary', max_length=255, blank=True)
    selection = models.CharField("selection", max_length=50, blank=False)
    us_e = models.CharField("use", max_length=255, blank=True)
    construction_feature = models.TextField("construction/features", blank=True)
    received_from = models.CharField("received from", max_length=255, blank=True)
    note = models.CharField("note", max_length=300, blank=True)
    reference = models.CharField("reference", max_length=255, blank=True)
    map = models.FileField("plasmid map (.dna)", help_text = 'only SnapGene .dna files, max. 2 MB', upload_to="collection_management/plasmid/dna/", blank=True)
    map_png = models.ImageField("plasmid image" , upload_to="collection_management/plasmid/png/", blank=True)
    map_gbk = models.FileField("plasmid map (.gbk)", upload_to="collection_management/plasmid/gbk/", help_text = 'only .gbk or .gb files, max. 2 MB', blank=True)

    created_date_time = models.DateTimeField("created", auto_now_add=True)
    created_approval_by_pi = models.BooleanField("record creation approval", default=False)
    last_changed_date_time = models.DateTimeField("last changed", auto_now=True)
    last_changed_approval_by_pi = models.NullBooleanField("record change approval", default=None)
    approval_by_pi_date_time = models.DateTimeField(null=True, default=None)
    approval = GenericRelation(RecordToBeApproved)
    approval_user = models.ForeignKey(User, related_name='plasmid_approval_user', on_delete=models.PROTECT, null=True)
    created_by = models.ForeignKey(User, related_name='plasmid_createdby_user', on_delete=models.PROTECT)
    history = HistoricalRecords()

    formz_projects = models.ManyToManyField(FormZProject, verbose_name='projects', related_name='plasmid_formz_projects', blank= False)
    formz_risk_group = models.PositiveSmallIntegerField('risk group', choices=((1,1), (2,2)), blank=False, null=True)
    destroyed_date = models.DateField("destroyed", blank=True, null=True)
    vector_zkbs = models.ForeignKey(ZkbsPlasmid, verbose_name = 'ZKBS database vector', on_delete=models.PROTECT, blank=False, null=True,
                                    help_text='The backbone of the plasmid, from the ZKBS database. If not applicable, choose none. <a href="/formz/zkbsplasmid/" target="_blank">View all</a>')
    formz_elements = models.ManyToManyField(FormZBaseElement, verbose_name ='elements', blank=True,
                                            help_text='<a href="/formz/formzbaseelement/" target="_blank">View all/Change</a>')
    formz_gentech_methods = models.ManyToManyField(GenTechMethod, verbose_name='genTech methods', related_name='plasmid_gentech_method', blank= True,
                                                    help_text='The methods used to create the plasmid')
    formz_ecoli_strains = models.ManyToManyField('EColiStrain', verbose_name='e. coli strains', related_name='plasmid_ecoli_strains', blank= False)

    # Fields to keep a record of M2M field values in the main plasmid record: IDs for formz_projects
    # and names for formz_elements
    history_formz_projects = models.TextField("formZ projects", blank=True)
    history_formz_elements = models.TextField("formZ elements", blank=True)
    history_formz_gentech_methods = models.TextField("genTech methods", blank=True)
    history_formz_ecoli_strains = models.TextField("e. coli strains", blank=True)
    
    class Meta:
        verbose_name = 'plasmid'
        verbose_name_plural = 'plasmids'

    def clean(self):
        
        errors = []
        
        file_size_limit = 2 * 1024 * 1024
        
        if self.map:
            
            # Check if file is bigger than 2 MB
            if self.map.size > file_size_limit:
                errors.append(ValidationError('Plasmid map too large. Size cannot exceed 2 MB.'))
        
            # Check if file's extension is '.dna'
            try:
                map_ext = self.map.name.split('.')[-1].lower()
            except:
                map_ext = None
            if map_ext == None or map_ext != 'dna':
                errors.append(ValidationError('Invalid file format. Please select a valid SnapGene .dna file'))
            else:
                
                # Check if .dna file is a real SnapGene file

                dna_map_handle = self.map.open('rb')
                
                first_byte = dna_map_handle.read(1)
                dna_map_handle.read(4)
                title = dna_map_handle.read(8).decode('ascii')
                if first_byte != b'\t' and title != 'SnapGene':
                    errors.append(ValidationError('Invalid file format. Please select a valid SnapGene .dna file'))

        if self.map_gbk:
            
            # Check if file is bigger than 2 MB
            if self.map_gbk.size > file_size_limit:
                errors.append(ValidationError('Plasmid map too large. Size cannot exceed 2 MB.'))
        
            # Check if file's extension is '.gbk'
            try:
                map_ext = self.map_gbk.name.split('.')[-1].lower()
            except:
                map_ext = None
            if map_ext == None or map_ext not in ['gbk', 'gb']:
                errors.append(ValidationError('Invalid file format. Please select a valid GenBank (.gbk or .gb) file'))

        if len(errors) > 0:
            raise ValidationError(errors)

    def __str__(self):
        return "{} - {}".format(self.id, self.name)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        
        # If destroyed date not present, automatically set it
        if not self.destroyed_date:
            self.destroyed_date = datetime.now().date() + timedelta(days=random.randint(7,21))
        
        super(Plasmid, self).save(force_insert, force_update, using, update_fields)

    def get_all_instock_plasmids(self):
        """Returns all plasmids present in the stocked organism"""

        return None

    def get_all_transient_episomal_plasmids(self):
        """Returns all transiently transformed episomal plasmids"""

        return None
    
    def get_all_plasmid_maps(self):
        """Returns self is has map"""
        
        if self.map:
            return [self]
        else:
            return None

    def get_all_uncommon_formz_elements(self):
        """Returns all uncommon features in stocked organism"""

        elements = self.formz_elements.filter(common_feature=False).order_by('name')
        return elements
    
    def get_all_common_formz_elements(self):
        """Returns all common features in stocked organism"""

        elements = self.formz_elements.filter(common_feature=True).order_by('name')
        return elements

    def convert_plasmid_map_to_base64(self):
        import base64
        """Returns html image element for map"""

        png_data = base64.b64encode(open(self.map_png.path,'rb').read()).decode('ascii')
        return str(png_data)

    def utf8_encoded_gbk(self):

        """Returns a decoded gbk plasmid map"""

        return self.map_gbk.read().decode()

#################################################
#                     OLIGO                     #
#################################################

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
    last_changed_approval_by_pi = models.NullBooleanField("record change approval", default=None)
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

#################################################
#               SC. POMBE STRAIN                #
#################################################

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
    last_changed_approval_by_pi = models.NullBooleanField("record change approval", default=None)
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
                                            '<a href="/formz/formzbaseelement/" target="_blank">View all/Change</a>', blank=True)
    destroyed_date = models.DateField("destroyed", blank=True, null=True)

    # Fields to keep a record of M2M field values (only IDs!) in the main strain record
    history_integrated_plasmids = models.TextField("integrated plasmid", blank=True)
    history_cassette_plasmids = models.TextField("cassette plasmids", blank=True)
    history_episomal_plasmids = models.TextField("episomal plasmids", blank=True)
    history_all_plasmids_in_stocked_strain = models.TextField("all plasmids in stocked strain",blank=True) # Integrated, cassete and episomal (only if present in -80 stock)
    history_formz_projects = models.TextField("formZ projects", blank=True)
    history_formz_gentech_methods = models.TextField("genTech methods", blank=True)
    history_formz_elements = models.TextField("formz elements", blank=True)
    
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

    def get_all_plasmid_maps(self):
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

#################################################
#                E. COLI STRAIN                 #
#################################################

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
    last_changed_approval_by_pi = models.NullBooleanField("record change approval", default=None)
    approval_by_pi_date_time = models.DateTimeField(null=True, default=None)
    approval = GenericRelation(RecordToBeApproved)
    approval_user = models.ForeignKey(User, related_name='coli_approval_user', on_delete=models.PROTECT, null=True)
    created_by = models.ForeignKey(User, related_name='coli_createdby_user', on_delete=models.PROTECT)
    history = HistoricalRecords()

    formz_projects = models.ManyToManyField(FormZProject, verbose_name='formZ projects', related_name='coli_formz_project', blank=False)
    formz_elements = models.ManyToManyField(FormZBaseElement, verbose_name ='elements', related_name='coli_formz_element', blank=True)
    destroyed_date = models.DateField("destroyed", blank=True, null=True)

    history_formz_projects = models.TextField("formZ projects", blank=True)
    history_formz_gentech_methods = models.TextField("genTech methods", blank=True)
    history_formz_elements = models.TextField("formz elements", blank=True)

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

################################################
#                   CELL LINE                  #
################################################

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
    last_changed_approval_by_pi = models.NullBooleanField("record change approval", default=None)
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
                                            help_text='Use only when an element is not present in the chosen plasmid(s), if any', blank=True)
    
    destroyed_date = models.DateField("destroyed", blank=True, null=True)

    # Fields to keep a record of M2M field values (only IDs!) in the main strain record
    history_integrated_plasmids = models.TextField("integrated plasmid", blank=True)
    history_episomal_plasmids = models.TextField("episomal plasmids", blank=True)
    history_formz_projects = models.TextField("formZ projects", blank=True)
    history_formz_gentech_methods = models.TextField("genTech methods", blank=True)
    history_formz_elements = models.TextField("formz elements", blank=True)
    history_documents = models.TextField("documents", blank=True)
    
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

################################################
#               CELL LINE DOC                  #
################################################

CELL_LINE_DOC_TYPE_CHOICES = (
    ("virus", "Virus test"),
    ("mycoplasma", "Mycoplasma test"), 
    ("fingerprint", "Fingerprinting"), 
    ("other", "Other"))

class CellLineDoc(models.Model):
    
    name = models.FileField("file name", help_text = 'max. 2 MB', upload_to="temp/", blank=False, null=True)
    typ_e = models.CharField("doc type", max_length=255, choices=CELL_LINE_DOC_TYPE_CHOICES, blank=False)
    date_of_test = models.DateField("date of test", blank=False, null=True)
    comment = models.CharField("comment", max_length=150, blank=True)
    cell_line = models.ForeignKey(CellLine, on_delete=models.PROTECT)
    
    created_date_time = models.DateTimeField("created", auto_now_add=True)
    last_changed_date_time = models.DateTimeField("last Changed", auto_now=True)
    
    RENAME_FILES = {
        'name': 
        {'dest': 'collection_management/celllinedoc/', 'keep_ext': True}
        }

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        
        # Rename a file of any given name to mclXX_date-uploaded_time-uploaded.ext,
        # after the corresponding entry has been created
        
        rename_files = getattr(self, 'RENAME_FILES', None)
        
        if rename_files:
            
            super(CellLineDoc, self).save(force_insert, force_update, using, update_fields)
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
                        final_name = os.path.join(final_dest, "cl" + LAB_ABBREVIATION_FOR_FILES + str(self.cell_line.id) + "_" + self.typ_e + "_" + time.strftime("%Y%m%d") + "_" + time.strftime("%H%M%S") + "_" + str(self.id))
                        if keep_ext:
                            final_name += ext
                    
                    # Essentially, rename file 
                    if file_name != final_name:
                        field.storage.delete(final_name)
                        field.storage.save(final_name, field)
                        field.close()
                        field.storage.delete(file_name)
                        setattr(self, field_name, final_name)
        
        super(CellLineDoc, self).save(force_insert, force_update, using, update_fields)

    class Meta:
        verbose_name = 'cell line document'
    
    def __str__(self):
         return str(self.id)

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
#                   ANTIBODY                    #
#################################################

class Antibody (models.Model, SaveWithoutHistoricalRecord):
    
    name = models.CharField("name", max_length = 255, blank=False)
    species_isotype = models.CharField("species/isotype", max_length = 255, blank=False)
    clone = models.CharField("clone", max_length = 255, blank=True)
    received_from = models.CharField("received from", max_length = 255, blank=True)
    catalogue_number = models.CharField("catalogue number", max_length = 255, blank=True)
    l_ocation = models.CharField("location", max_length = 255, blank=True)
    a_pplication = models.CharField("application", max_length = 255, blank=True)
    description_comment = models.TextField("description/comments", blank=True)
    info_sheet = models.FileField("info sheet", help_text = 'only .pdf files, max. 2 MB', upload_to="collection_management/antibody/", blank=True, null=True)

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
        verbose_name = 'antibody'
        verbose_name_plural = 'antibodies'
    
    def __str__(self):
        return str(self.id)