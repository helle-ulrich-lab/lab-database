from django.db import models
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.contrib.auth.models import User
from django.forms import ValidationError
from django.contrib.contenttypes.fields import GenericRelation


from datetime import timedelta, datetime
import random
from urllib.parse import urlencode

from simple_history.models import HistoricalRecords

from approval.models import RecordToBeApproved
from common.models import SaveWithoutHistoricalRecord
from formz.models import FormZBaseElement
from formz.models import FormZProject
from formz.models import GenTechMethod
from formz.models import ZkbsPlasmid
from common.models import DocFileMixin
from common.models import DownloadFileNameMixin

LAB_ABBREVIATION_FOR_FILES = getattr(settings, 'LAB_ABBREVIATION_FOR_FILES', '')
OVE_URL = getattr(settings, 'OVE_URL', '')


class Plasmid (DownloadFileNameMixin, models.Model, SaveWithoutHistoricalRecord):
    
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
    map = models.FileField("plasmid map (.dna)", help_text = 'only SnapGene .dna files, max. 2 MB', upload_to="collection/plasmid/dna/", blank=True)
    map_png = models.ImageField("plasmid image" , upload_to="collection/plasmid/png/", blank=True)
    map_gbk = models.FileField("plasmid map (.gbk)", upload_to="collection/plasmid/gbk/", help_text = 'only .gbk or .gb files, max. 2 MB', blank=True)

    created_date_time = models.DateTimeField("created", auto_now_add=True)
    created_approval_by_pi = models.BooleanField("record creation approval", default=False)
    last_changed_date_time = models.DateTimeField("last changed", auto_now=True)
    last_changed_approval_by_pi = models.BooleanField("record change approval", default=None, null=True)
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
                                            help_text= 'Searching against the aliases of an element is case-sensitive. '
                                            '<a href="/formz/formzbaseelement/" target="_blank">View all/Change</a>')
    formz_gentech_methods = models.ManyToManyField(GenTechMethod, verbose_name='genTech methods', related_name='plasmid_gentech_method', blank= True,
                                                    help_text='The methods used to create the plasmid')
    formz_ecoli_strains = models.ManyToManyField('EColiStrain', verbose_name='e. coli strains', related_name='plasmid_ecoli_strains', blank= False)

    # Fields to keep a record of M2M field values in the main plasmid record: IDs for formz_projects
    # and names for formz_elements
    history_formz_projects = ArrayField(models.PositiveIntegerField(), verbose_name="formZ projects", blank=True, null=True)
    history_formz_elements = ArrayField(models.PositiveIntegerField(), verbose_name="formz elements", blank=True, null=True)
    history_formz_gentech_methods = ArrayField(models.PositiveIntegerField(), verbose_name="genTech methods", blank=True, null=True)
    history_formz_ecoli_strains = ArrayField(models.PositiveIntegerField(), verbose_name="e. coli strains", blank=True, null=True)
    history_documents = ArrayField(models.PositiveIntegerField(), verbose_name="documents", blank=True, null=True)

    _model_abbreviation = 'p'

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

    def get_ove_url_map(self):

        """Returns the url to view the a SnapGene file in OVE"""

        params = {'file_name': self.map.url,
                  'title': f'p{LAB_ABBREVIATION_FOR_FILES}{self.__str__()}',
                  'file_format': 'dna'}

        return f'{OVE_URL}?{urlencode(params)}'

    def get_ove_url_map_gbk(self):

        """Returns the url to view the a gbk file in OVE"""

        params = {'file_name': self.map_gbk.url,
                  'title': f'p{LAB_ABBREVIATION_FOR_FILES}{self.__str__()}',
                  'file_format': 'gbk'}

        return f'{OVE_URL}?{urlencode(params)}'

    def get_ove_url_find_oligos_map_gbk(self):

        """Returns the url to import all oligos into the plasmid map 
           and view it in OVE"""

        params = {'file_name': f'/{self._meta.app_label}/{self._meta.model_name}/{self.pk}/find_oligos/',
                  'title': f'p{LAB_ABBREVIATION_FOR_FILES}{self.__str__()} (imported oligos)',
                  'file_format': 'gbk',
                  'show_oligos': 'true'}

        return f'{OVE_URL}?{urlencode(params)}'

class PlasmidDoc(DocFileMixin):
    plasmid = models.ForeignKey(Plasmid, on_delete=models.PROTECT)

    _mixin_props = {'destination_dir': 'collection/plasmiddoc/',
                    'file_prefix': 'pDoc',
                    'parent_field_name': 'plasmid'}

    class Meta:
        verbose_name = 'plasmid document'