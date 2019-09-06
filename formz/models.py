#################################################
#    DJANGO 'CORE' FUNCTIONALITIES IMPORTS      #
#################################################

from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

#################################################
#                 MODEL CLASSES                 #
#################################################

class NucleicAcidPurity (models.Model):
    
    english_name = models.CharField("English name", max_length=255, blank=False)
    german_name = models.CharField("German name", max_length=255, blank=False)

    class Meta:        
        verbose_name = 'nuclei acid purity'
        verbose_name_plural = 'nuclei acid purities'
        ordering = ["english_name",]
    
    def __str__(self):
        return str(self.english_name)

class NucleicAcidRisk (models.Model):
    
    english_name = models.CharField("English name", max_length=255, blank=False)
    german_name = models.CharField("German name", max_length=255, blank=False)

    class Meta:        
        verbose_name = 'nuclei acid risk potential'
        verbose_name_plural = 'nuclei acid risk potentials'
        ordering = ["english_name",]
    
    def __str__(self):
        return str(self.english_name)

class GenTechMethod (models.Model):
        
    english_name = models.CharField("English name", max_length=255, blank=False)
    german_name = models.CharField("German name", max_length=255, blank=False)

    class Meta:
        verbose_name = 'genTech method'
        verbose_name_plural = 'genTech methods'
        ordering = ["english_name",]
    
    def __str__(self):
        return str(self.english_name)

class FormZProject (models.Model):

    title = models.CharField("title", help_text = '<i>Titel</i>', max_length=255, blank=False)
    short_title = models.CharField("short title", help_text = '<i>Kurzer Titel</i>', max_length=255, blank=False)
    short_title_english = models.CharField("English short title", max_length=255, blank=False)
    parent_project = models.ForeignKey('self', verbose_name = 'parent project', on_delete=models.PROTECT, blank=True, null=True)

    safety_level = models.PositiveSmallIntegerField('safety level', help_text='<i>Sicherheitsstufe</i>', choices=((1,1), (2,2)), blank=False, null=True)
    project_leader = models.CharField("project leader", help_text='<i>Projektleiter</i>', max_length=255, blank=False)
    objectives = models.CharField("objectives of strategy", help_text='<i>Zielsetzung</i>', max_length=255, blank=True)
    description = models.TextField("Description of strategy/performance", help_text= 'Techniques, organisms, plasmids, etc. <i>Beschreibung der Durchführung</i>', blank=True)
    donor_organims = models.CharField("donor organisms", help_text='Used organisms, their risk group and safety-relevant properties. '
                                      '<i>Verwendete Spenderorganismen</i>', max_length=255, blank=True)
    potential_risk_nuc_acid = models.TextField("potential risks of transferred nucleic acids", help_text='Include safety-relevant properties. '
                                               '<i>Gefährdungspotentiale der übertragenen Nukleinsäuren</i>', blank=True)
    vectors = models.TextField("Vectors", help_text='Include safety-relevant properties', blank=True)
    recipient_organisms = models.CharField("recipient organisms", help_text='Include risk groups and safety-relevant properties. '
                                           '<i>Verwendete Empfängerorganismen</i>', max_length=255, blank=True)
    generated_gmo = models.TextField("generated GMOs", help_text='Include risk groups and safety-relevant properties. '
                                     '<i>Erzeugte GVO</i>', blank=True)
    hazard_activity = models.TextField("hazard-relevant characteristics of activity", help_text= '<i>Gefährdungsrelevante Merkmale der Tätigkeit</i>', blank=True)
    hazards_employee = models.TextField("severity and likelihood of hazards to employees and/or the environment",
                                        help_text='<i>Schwere und Wahrscheinlichkeit einer Gefährdung der Mitarbeiter und/oder der Umwelt</i>', blank=True)

    beginning_work_date = models.DateField("beginning of work", help_text='<i>Beginn der Arbeiten</i>', blank=False, null=True)
    end_work_date = models.DateField("end of work", help_text='<i>Ende der Arbeiten</i>', blank=True, null=True)

    class Meta:        
        verbose_name = 'project'
        verbose_name_plural = 'projects'
        ordering = ["id",]

    def __str__(self):
        return str(self.short_title_english)

class ZkbsPlasmid (models.Model):
    
    name = models.CharField("name", max_length=255, blank=False)
    source = models.CharField("source", max_length=255, blank=False)
    purpose = models.CharField("purpose", max_length=255, blank=False)
    description = models.TextField("description", blank=True)

    class Meta:
        verbose_name = 'ZKBS plasmid'
        verbose_name_plural = 'ZKBS plasmids'
        ordering = ["name",]

    def __str__(self):
        return str(self.name)

class ZkbsOncogene (models.Model):
    
    name = models.CharField("name", max_length=255, blank=False)
    synonym = models.CharField("synonym", max_length=255)
    species = models.CharField("species", max_length=255, blank=False)
    risk_potential = models.CharField("risk potential", max_length=255, blank=False)
    reference = models.TextField("description")
    additional_measures = models.BooleanField("additional measures?", blank=True)

    class Meta:
        verbose_name = 'ZKBS oncogene'
        verbose_name_plural = 'ZKBS oncogenes'
        ordering = ["name",]

    def __str__(self):
        return str(self.name)

class ZkbsCellLine (models.Model):
    
    name = models.CharField("name", max_length=255, blank=False)
    synonym = models.CharField("synonym", max_length=255, blank=True)
    organism = models.CharField("organism", max_length=255, blank=False)
    risk_potential = models.CharField("risk potential", max_length=255, blank=False)
    origin = models.CharField("origin", max_length=255)
    virus = models.CharField("virus", max_length=255)
    genetically_modified = models.BooleanField("genetically modified?", blank=True)

    class Meta:
        verbose_name = 'ZKBS cell line'
        verbose_name_plural = 'ZKBS cell lines'
        ordering = ["name",]

    def __str__(self):
        return str(self.name)

class FormZBaseElement (models.Model):

    name = models.CharField("name", max_length=255, help_text='Must be identical (CASE-SENSITIVE!) to a feature name in a plasmid map for auto-detection to work. '
                            'If you want to associate additional names to an element, add them as aliases below', unique=True, blank=True)
    donor_organism = models.CharField("donor organism", help_text = "As species, e.g. Homo sapiens; use none if no organism applies", max_length=255, blank=True)
    donor_organism_risk = models.PositiveSmallIntegerField('risk group', choices=((1,1), (2,2)), blank=True, null=True)
    nuc_acid_purity = models.ForeignKey(NucleicAcidPurity, verbose_name = 'nucleic acid purity', on_delete=models.PROTECT, blank=True, null=True)
    nuc_acid_risk = models.ForeignKey(NucleicAcidRisk, verbose_name = 'nucleic acid risk potential', on_delete=models.PROTECT, blank=True, null=True)
    zkbs_oncogene = models.ForeignKey(ZkbsOncogene, verbose_name = 'ZKBS database oncogene', on_delete=models.PROTECT, blank=True, null=True,
                                      help_text='<a href="/formz/zkbsoncogene/" target="_blank">View</a>')
    description = models.TextField("description", blank=True)
    common_feature = models.BooleanField("is this a common plasmid feature?", blank=True)

    class Meta:
        verbose_name = 'sequence element'
        verbose_name_plural = 'sequence elements'
        ordering = ["name",]

    def __str__(self):
        return str(self.name)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        
        # Remove any leading and trailing white spaces from name field
        self.name = self.name.strip()
        
        super(FormZBaseElement, self).save(force_insert, force_update, using, update_fields)

class FormZBaseElementExtraLabel (models.Model):
    label = models.CharField("alias", max_length=255, blank=True)
    formz_base_element = models.ForeignKey(FormZBaseElement, on_delete=models.PROTECT, related_name='extra_label')

    class Meta:
        verbose_name = 'base element alias'
        verbose_name_plural = 'base element aliases'
        ordering = ["label",]

    def __str__(self):
        return str(self.label)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        
        # Remove any leading and trailing white spaces from name field
        self.label = self.label.strip()
        
        super(FormZBaseElementExtraLabel, self).save(force_insert, force_update, using, update_fields)

class FormZHeader (models.Model):
    
    operator = models.CharField("operator", max_length=255, help_text = 'Name des Betreibers', blank=False)
    address = models.TextField("address of bioengineering facility", help_text = 'Anschrift der gentechnischen Anlage', blank=False)
    name_biosafety_officer = models.CharField("name of the biosafety officer", max_length=255, help_text = 'Name des Beauftragten für die Biologische Sicherheit', blank=False)

    s1_approval_file_num = models.CharField("file number for S1 approval", max_length=255, help_text = 'e.g. 21-29,8 B 56.01; TgbNr.: 8/29,0/11/36',blank=False)
    s1_approval_date = models.DateField("S1 approval date", blank=False, null=True)
    s2_approval_file_num = models.CharField("file number for S2 approval", max_length=255, help_text = 'e.g. 29,8 B 56.02:21; TgbNr.: 8/29,0/13/46', blank=False)
    s2_approval_date = models.DateField("S2 approval date", blank=False, null=True)

    class Meta:        
        verbose_name = 'header'
        verbose_name_plural = 'headers'

    def __str__(self):
        return str(self.operator)

class FormZStorageLocation (models.Model):

    collection_model = models.OneToOneField(ContentType, verbose_name='collection', help_text = 'Strain, plasmids, cell lines, etc.', on_delete=models.PROTECT, blank=False, null=True, unique=True)
    storage_location = models.CharField("storage location", help_text='Room where the collection is stored', max_length=255, blank=False)
    species_name = models.CharField("species name", help_text="Full species name, e.g. Homo sapiens" , max_length=255, blank=True)

    class Meta:        
        verbose_name = 'storage location'
        verbose_name_plural = 'storage locations'

    def __str__(self):
        return str(self.storage_location)