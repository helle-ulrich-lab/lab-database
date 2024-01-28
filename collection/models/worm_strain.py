from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericRelation
from django.forms import ValidationError

from simple_history.models import HistoricalRecords

from approval.models import RecordToBeApproved
from common.models import SaveWithoutHistoricalRecord
from formz.models import FormZBaseElement
from formz.models import FormZProject
from formz.models import GenTechMethod
from collection.models import Plasmid
from collection.models import Oligo


WORM_SPECIES_CHOICES = (
    ('celegans','Caenorhabditis elegans'),
    ('cbriggsae','Caenorhabditis briggsae'),
    ('cinopinata','Caenorhabditis inopinata'),
    ('cjaponica','Caenorhabditis japonica'),
    ('ppacificus','Pristionchus pacificus')
)


class WormStrain (models.Model, SaveWithoutHistoricalRecord):

    name = models.CharField("name", max_length=255, blank=False)
    chromosomal_genotype = models.TextField("chromosomal genotype", blank=True)
    parent_1 = models.ForeignKey('self', verbose_name='Parent 1', on_delete=models.PROTECT, related_name='worm_parent_1', help_text='Main parental strain', blank=True, null=True)
    parent_2 = models.ForeignKey('self', verbose_name='Parent 2', on_delete=models.PROTECT, related_name='worm_parent_2', help_text='Only for crosses', blank=True, null=True)
    construction = models.TextField("construction", blank=True)
    outcrossed = models.CharField("outcrossed", max_length=255, blank=True)
    growth_conditions = models.CharField("growth conditions", max_length=255, blank=True)
    organism = models.CharField('organism', choices=WORM_SPECIES_CHOICES, max_length=15, default='celegans', blank=False)

    integrated_dna_plasmids = models.ManyToManyField(Plasmid, verbose_name='plasmids', related_name='worm_integrated_plasmid', blank= True)
    integrated_dna_oligos = models.ManyToManyField(Oligo, verbose_name='oligos', related_name='worm_integrated_oligo', blank= True)

    selection = models.CharField("selection", max_length=255, blank=True)
    phenotype = models.CharField("phenotype", max_length=255, blank=True)
    received_from = models.CharField("received from", max_length=255, blank=True)
    us_e = models.CharField("use", max_length=255, blank=True)
    note = models.CharField("note", max_length=255, blank=True)
    reference = models.CharField("reference", max_length=255, blank=True)

    location_freezer1 = models.CharField("location Freezer 1", max_length=10, blank=True)
    location_freezer2 = models.CharField("location Freezer 2", max_length=10, blank=True)
    location_backup = models.CharField("location Backup", max_length=10, blank=True)
    
    created_date_time = models.DateTimeField("created", auto_now_add=True)
    created_approval_by_pi = models.BooleanField("record creation approval", default=False)
    last_changed_date_time = models.DateTimeField("last changed", auto_now=True)
    last_changed_approval_by_pi = models.BooleanField("record change approval", default=None, null=True)
    approval_by_pi_date_time = models.DateTimeField(null = True, default=None)
    approval = GenericRelation(RecordToBeApproved)
    approval_user = models.ForeignKey(User, related_name='worm_approval_user', on_delete=models.PROTECT, null=True)
    created_by = models.ForeignKey(User, related_name='worm_createdby_user', on_delete=models.PROTECT)
    history = HistoricalRecords()

    formz_projects = models.ManyToManyField(FormZProject, verbose_name='projects', related_name='worm_formz_project', blank=False)
    formz_risk_group = models.PositiveSmallIntegerField('risk group', choices=((1,1), (2,2)), blank=False, null=True)
    formz_gentech_methods = models.ManyToManyField(GenTechMethod, verbose_name='genTech methods', related_name='worm_gentech_method', blank= True,
                                                    help_text='The methods used to create the strain')
    formz_elements = models.ManyToManyField(FormZBaseElement, verbose_name ='elements', related_name='worm_formz_element', 
                                            help_text='Use only when an element is not present in the chosen plasmid(s), if any. '
                                                      'Searching against the aliases of an element is case-sensitive. '
                                                      '<a href="/formz/formzbaseelement/" target="_blank">View all/Change</a>', blank=True)
    destroyed_date = models.DateField("destroyed", blank=True, null=True)

    # Fields to keep a record of M2M field values (only IDs!) in the main strain record
    history_integrated_plasmids = ArrayField(models.PositiveIntegerField(), verbose_name="integrated plasmids", blank=True, null=True)
    history_integrated_oligos = ArrayField(models.PositiveIntegerField(), verbose_name="integrated oligos", blank=True, null=True)
    history_formz_projects = ArrayField(models.PositiveIntegerField(), verbose_name="formZ projects", blank=True, null=True)
    history_formz_gentech_methods = ArrayField(models.PositiveIntegerField(), verbose_name="genTech methods", blank=True, null=True)
    history_formz_elements = ArrayField(models.PositiveIntegerField(), verbose_name="formz elements", blank=True, null=True)
    history_genotyping_oligos = ArrayField(models.PositiveIntegerField(), verbose_name="genotyping oligos", blank=True, null=True)

    class Meta:
        verbose_name = 'strain - Worm'
        verbose_name_plural = 'strains - Worm'
    
    def __str__(self):
        return "{} - {}".format(self.id, self.name)

    def get_all_uncommon_formz_elements(self):
        """Returns all uncommon features in stocked organism"""

        elements = self.formz_elements.all()
        all_plasmids = self.integrated_dna_plasmids.all()
        all_oligos = self.integrated_dna_oligos.all()
        for pl in all_plasmids:
            elements = elements | pl.formz_elements.all()
        for ol in all_oligos:
            elements = elements | ol.formz_elements.all()
        elements = elements.distinct().filter(common_feature=False).order_by('name')
        return elements
    
    def get_all_common_formz_elements(self):
        """Returns all common features in stocked organism"""

        elements = self.formz_elements.all()
        all_plasmids = self.integrated_dna_plasmids.all()
        all_oligos = self.integrated_dna_oligos.all()
        for pl in all_plasmids:
            elements = elements | pl.formz_elements.all()
        for ol in all_oligos:
            elements = elements | ol.formz_elements.all()
        elements = elements.distinct().filter(common_feature=True).order_by('name')
        return elements

    def get_all_instock_plasmids(self):
        """Returns all plasmids present in the stocked organism"""

        return self.integrated_dna_plasmids.all().distinct().order_by('id')

    def get_all_transient_episomal_plasmids(self):
        """Returns all transiently transformed episomal plasmids"""

        return None
    
    def get_all_plasmid_maps(self):
        """Returns all plasmids with a map"""
        return self.integrated_dna_plasmids.all().distinct().exclude(map='').order_by('id')

class WormStrainGenotypingAssay (models.Model):
    
    worm_strain = models.ForeignKey(WormStrain, on_delete=models.PROTECT)
    locus_allele = models.CharField("locus/allele", max_length=255, blank=False)
    oligos = models.ManyToManyField(Oligo, related_name='wormstrain_genotypingassay_oligo', blank=False)

    class Meta:
        verbose_name = 'worm strain genotyping assay'
        verbose_name_plural = 'worm strain genotyping assays'
    
    def __str__(self):
        return str(self.id)
