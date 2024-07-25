from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericRelation
from django.forms import ValidationError
from django.conf import settings

from simple_history.models import HistoricalRecords
from urllib.parse import urlencode

from approval.models import RecordToBeApproved
from common.models import SaveWithoutHistoricalRecord
from formz.models import FormZBaseElement
from formz.models import FormZProject
from formz.models import GenTechMethod
from collection.models import Plasmid
from collection.models import Oligo
from common.models import DocFileMixin


LAB_ABBREVIATION_FOR_FILES = getattr(settings, 'LAB_ABBREVIATION_FOR_FILES', '')
OVE_URL = getattr(settings, 'OVE_URL', '')
WORM_ALLELE_LAB_IDS = getattr(settings, 'WORM_ALLELE_LAB_IDS', None)
WORM_ALLELE_LAB_ID_DEFAULT = getattr(settings, 'WORM_ALLELE_LAB_ID_DEFAULT', '')


class WormStrainAllele(models.Model):

    _model_abbreviation = 'wa'
    _model_upload_to = 'collection/wormstrainallele/'
    german_name = 'Allel'

    lab_identifier = models.CharField('prefix/Lab identifier',
                                      choices=WORM_ALLELE_LAB_IDS,
                                      max_length=15,
                                      default=WORM_ALLELE_LAB_ID_DEFAULT,
                                      blank=False)
    typ_e = models.CharField("type",
                             choices=(('t', 'Transgene'), ('m', 'Mutation')),
                             max_length=5,
                             blank=False)

    transgene = models.CharField("transgene",
                             max_length=255,
                             blank=True)
    transgene_position = models.CharField("transgene position",
                             max_length=255,
                             blank=True)
    transgene_plasmids = models.CharField("Transgene plasmids",
                             max_length=255,
                             blank=True)

    mutation = models.CharField("mutation",
                             max_length=255,
                             blank=True)
    mutation_type = models.CharField("mutation type",
                             max_length=255,
                             blank=True)
    mutation_position = models.CharField("mutation position",
                                      max_length=255,
                                      blank=True)
    
    reference_strain = models.ForeignKey('WormStrain',
                                         verbose_name='reference strain',
                                         on_delete=models.PROTECT,
                                         related_name='allele_worm_reference_strain',
                                         blank=False,
                                         null=False)
    made_by_method = models.ForeignKey(GenTechMethod,
                                       verbose_name='made by method',
                                       related_name='allele_worm_method',
                                       help_text='The methods used to create the allele',
                                       on_delete=models.PROTECT,
                                       blank=False)
    made_by_person = models.CharField("made by person",
                                      max_length=255,
                                      blank=False)
    note = models.CharField("note",
                             max_length=255,
                             blank=True)

    map = models.FileField("map (.dna)",
                           help_text='only SnapGene .dna files, max. 2 MB',
                           upload_to=_model_upload_to + 'dna/',
                           blank=True)
    map_png = models.ImageField("map (.png)",
                                upload_to=_model_upload_to + 'png/',
                                blank=True)
    map_gbk = models.FileField("Map (.gbk)",
                               upload_to=_model_upload_to + 'gbk/',
                               help_text='only .gbk or .gb files, max. 2 MB',
                               blank=True)

    created_date_time = models.DateTimeField("created", auto_now_add=True)
    last_changed_date_time = models.DateTimeField("last changed",
                                                  auto_now=True)
    created_by = models.ForeignKey(User,
                                   related_name='wormstrainallele_createdby_user',
                                   on_delete=models.PROTECT)
    history = HistoricalRecords()

    formz_elements = models.ManyToManyField(FormZBaseElement,
                                            verbose_name='elements',
                                            help_text='Searching against the aliases of an element is case-sensitive. '
                                            '<a href="/formz/formzbaseelement/" target="_blank">View all/Change</a>',
                                            blank=True)

    # Fields to keep a record of M2M field values in the main plasmid record: IDs for formz_projects
    # and names for formz_elements
    history_formz_elements = ArrayField(models.PositiveIntegerField(),
                                        verbose_name="formz elements",
                                        blank=True,
                                        null=True,
                                        default=list)

    class Meta:
        verbose_name = 'allele - Worm'
        verbose_name_plural = 'alleles - Worm'

    def clean(self):

        errors = []

        file_size_limit = 2 * 1024 * 1024

        if self.map:

            # Check if file is bigger than 2 MB
            if self.map.size > file_size_limit:
                errors.append(ValidationError('The map is too large. Size cannot exceed 2 MB.'))

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
                errors.append(ValidationError('The map is too large. Size cannot exceed 2 MB.'))

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
        return f"{self.lab_identifier}{self.id} - {self.name}"

    @property
    def name(self):
        return self.transgene or self.mutation
    
    @property
    def download_file_name(self):
        return self.__str__()

    def get_all_uncommon_formz_elements(self):
        """Returns all uncommon features in stocked organism"""

        elements = self.formz_elements. \
                   filter(common_feature=False). \
                   order_by('name')
        return elements

    def get_all_common_formz_elements(self):
        """Returns all common features in stocked organism"""

        elements = self.formz_elements. \
            filter(common_feature=True). \
            order_by('name')
        return elements

    def convert_png_map_to_base64(self):
        import base64
        """Returns html image element for map"""

        png_data = base64.b64encode(open(self.map_png.path, 'rb').read()).decode('ascii')
        return str(png_data)

    def utf8_encoded_gbk(self):
        """Returns a decoded gbk plasmid map"""

        return self.map_gbk.read().decode()

    def get_ove_url_map(self):
        """Returns the url to view the a SnapGene file in OVE"""

        params = {'file_name': self.map.url,
                  'title': self.__str__(),
                  'file_format': 'dna'}

        return f'{OVE_URL}?{urlencode(params)}'

    def get_ove_url_map_gbk(self):
        """Returns the url to view the a gbk file in OVE"""

        params = {'file_name': self.map_gbk.url,
                  'title': self.__str__(),
                  'file_format': 'gbk'}

        return f'{OVE_URL}?{urlencode(params)}'

    def get_ove_url_find_oligos_map_gbk(self):
        """Returns the url to import all oligos into the map
           and view it in OVE"""

        params = {'file_name': f'/{self._meta.app_label}/{self._meta.model_name}/{self.pk}/find_oligos/',
                  'title': f'{self.__str__()} (imported oligos)',
                  'file_format': 'gbk',
                  'show_oligos': 'true'}

        return f'{OVE_URL}?{urlencode(params)}'


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

    alleles = models.ManyToManyField(WormStrainAllele, verbose_name='alleles', related_name='worm_alleles', blank=True)
    
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
    history_integrated_dna_plasmids = ArrayField(models.PositiveIntegerField(), verbose_name="integrated plasmids", blank=True, null=True, default=list)
    history_integrated_dna_oligos = ArrayField(models.PositiveIntegerField(), verbose_name="integrated oligos", blank=True, null=True, default=list)
    history_formz_projects = ArrayField(models.PositiveIntegerField(), verbose_name="formZ projects", blank=True, null=True, default=list)
    history_formz_gentech_methods = ArrayField(models.PositiveIntegerField(), verbose_name="genTech methods", blank=True, null=True, default=list)
    history_formz_elements = ArrayField(models.PositiveIntegerField(), verbose_name="formz elements", blank=True, null=True, default=list)
    history_genotyping_oligos = ArrayField(models.PositiveIntegerField(), verbose_name="genotyping oligos", blank=True, null=True, default=list)
    history_documents = ArrayField(models.PositiveIntegerField(), verbose_name="documents", blank=True, null=True, default=list)
    history_alleles = ArrayField(models.PositiveIntegerField(), verbose_name="alleles", blank=True, null=True, default=list)

    _model_abbreviation = 'w'

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
        all_alleles = self.alleles.all()
        for pl in all_plasmids:
            elements = elements | pl.formz_elements.all()
        for ol in all_oligos:
            elements = elements | ol.formz_elements.all()
        for al in all_alleles:
            elements = elements | al.formz_elements.all()
        elements = elements.distinct().filter(common_feature=False).order_by('name')
        return elements
    
    def get_all_common_formz_elements(self):
        """Returns all common features in stocked organism"""

        elements = self.formz_elements.all()
        all_plasmids = self.integrated_dna_plasmids.all()
        all_oligos = self.integrated_dna_oligos.all()
        all_alleles = self.alleles.all()
        for pl in all_plasmids:
            elements = elements | pl.formz_elements.all()
        for ol in all_oligos:
            elements = elements | ol.formz_elements.all()
        for al in all_alleles:
            elements = elements | al.formz_elements.all()
        elements = elements.distinct().filter(common_feature=True).order_by('name')
        return elements

    def get_all_instock_plasmids(self):
        """Returns all plasmids present in the stocked organism"""

        return self.integrated_dna_plasmids.all().distinct().order_by('id')

    def get_all_transient_episomal_plasmids(self):
        """Returns all transiently transformed episomal plasmids"""

        return None
    
    def get_all_maps(self):
        """Returns all plasmids and alleles with a map"""

        return list(self.alleles.all().distinct().exclude(map='').order_by('id')) + \
               list(self.integrated_dna_plasmids.all().distinct().exclude(map='').order_by('id'))

class WormStrainGenotypingAssay (models.Model):
    
    worm_strain = models.ForeignKey(WormStrain, on_delete=models.PROTECT)
    locus_allele = models.CharField("locus/allele", max_length=255, blank=False)
    oligos = models.ManyToManyField(Oligo, related_name='wormstrain_genotypingassay_oligo', blank=False)

    class Meta:
        verbose_name = 'worm strain genotyping assay'
        verbose_name_plural = 'worm strain genotyping assays'
    
    def __str__(self):
        return str(self.id)

class WormStrainDoc(DocFileMixin):
    worm_strain = models.ForeignKey(WormStrain, on_delete=models.PROTECT)

    _mixin_props = {'destination_dir': 'collection/wormstraindoc/',
                    'file_prefix': 'wDoc',
                    'parent_field_name': 'worm_strain'}

    class Meta:
        verbose_name = 'worm strain document'