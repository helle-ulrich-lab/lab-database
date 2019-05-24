#################################################
#    DJANGO 'CORE' FUNCTIONALITIES IMPORTS      #
#################################################

from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

#################################################
#                GENERAL CLASSES                #
#################################################

class NucleicAcidPurity (models.Model):
    
    english_name = models.CharField("English name", max_length=255, blank=False)
    german_name = models.CharField("German name", max_length=255, blank=False)

    class Meta:
        '''Set a custom name to be used throughout the admin pages'''
        
        verbose_name = 'nuclei acid purity'
        verbose_name_plural = 'nuclei acid purities'
    
    def __str__(self):
        '''Set what to show as an object's unicode attribute, in this case
        it is just the ID of the object, but it could be its name'''
        
        return str(self.english_name)

class NucleicAcidRisk (models.Model):
    
    english_name = models.CharField("English name", max_length=255, blank=False)
    german_name = models.CharField("German name", max_length=255, blank=False)

    class Meta:
        '''Set a custom name to be used throughout the admin pages'''
        
        verbose_name = 'nuclei acid risk potential'
        verbose_name_plural = 'nuclei acid risk potentials'
    
    def __str__(self):
        '''Set what to show as an object's unicode attribute, in this case
        it is just the ID of the object, but it could be its name'''
        
        return str(self.english_name)

class GenTechMethod (models.Model):
        
    english_name = models.CharField("English name", max_length=255, blank=False)
    german_name = models.CharField("German name", max_length=255, blank=False)

    class Meta:
        '''Set a custom name to be used throughout the admin pages'''
        
        verbose_name = 'genTech method'
        verbose_name_plural = 'genTech methods'
    
    def __str__(self):
        '''Set what to show as an object's unicode attribute, in this case
        it is just the ID of the object, but it could be its name'''
        
        return str(self.english_name)

class FormZProject (models.Model):

    title = models.CharField("title", max_length=191, blank=False)

    safety_level = models.PositiveSmallIntegerField('safety level', choices=((1,1), (2,2)), blank=False, null=True)
    project_leader = models.CharField("project leader", max_length=255, blank=False)
    objectives = models.CharField("objectives of strategy", max_length=255, blank=True)
    description = models.TextField("Description of stratagy/performance", help_text= 'Techniques, organisms, plasmids, etc.', blank=True)
    donor_organims = models.CharField("donor organisms", help_text='Used organisms, their risk group and safety-relevant properties', max_length=255, blank=True)
    potential_risk_nuc_acid = models.TextField("potential risks of transferred nucleic acids", help_text='Include safety-relevant properties', blank=True)
    vectors = models.TextField("Vectors", help_text='Include safety-relevant properties', blank=True)
    recipient_organisms = models.CharField("recipient organisms", help_text='Include risk groups and safety-relevant properties', max_length=255, blank=True)
    generated_gmo = models.TextField("generated GMOs", help_text='Include risk groups and safety-relevant properties', blank=True)
    hazard_activity = models.TextField("hazard-relevant characteristics of activity", blank=True)
    hazards_employee = models.TextField("severity and likelihood of hazards to employees and/or the environment", blank=True)

    beginning_work_date = models.DateField("beginning of work", blank=False, null=True)
    end_work_date = models.DateField("end of work", blank=True, null=True)

    # collection_models = models.ManyToManyField(ContentType, verbose_name='collection models', help_text = '', on_delete=models.PROTECT, blank=False, null=True)

    class Meta:
        '''Set a custom name to be used throughout the admin pages'''
        
        verbose_name = 'project'
        verbose_name_plural = 'projects'

    def __str__(self):
        '''Set what to show as an object's unicode attribute, in this case
        it is just the ID of the object, but it could be its name'''
        
        return str(self.title)

class ZkbsPlasmid (models.Model):
    
    name = models.CharField("name", max_length=255, blank=False)
    source = models.CharField("source", max_length=255, blank=False)
    purpose = models.CharField("purpose", max_length=255, blank=False)
    description = models.TextField("description", blank=True)

    class Meta:
        '''Set a custom name to be used throughout the admin pages'''
        
        verbose_name = 'ZKBS plasmid'
        verbose_name_plural = 'ZKBS plasmids'

    def __str__(self):
        '''Set what to show as an object's unicode attribute, in this case
        it is just the ID of the object, but it could be its name'''
        
        return str(self.name)

class FormZBaseElement (models.Model):

    name = models.CharField("name", max_length=255, blank=True)
    donor_organism = models.CharField("donor organism", max_length=255, blank=True)
    donor_organism_risk = models.PositiveSmallIntegerField('risk group', choices=((1,1), (2,2)), blank=True, null=True)
    nuc_acid_type = models.CharField("nucleic acid type", max_length=255, blank=True)
    nuc_acid_purity = models.ForeignKey(NucleicAcidPurity, verbose_name = 'nucleic acid purity', on_delete=models.PROTECT, blank=True, null=True)
    nuc_acid_risk = models.ForeignKey(NucleicAcidRisk, verbose_name = 'nucleic acid risk potential', on_delete=models.PROTECT, blank=True, null=True)

    class Meta:
        '''Set a custom name to be used throughout the admin pages'''
        
        verbose_name = 'base element'
        verbose_name_plural = 'base elements'

    def __str__(self):
        '''Set what to show as an object's unicode attribute, in this case
        it is just the ID of the object, but it could be its name'''
        
        return str(self.name)

class FormZHeader (models.Model):
    
    operator = models.CharField("operator", max_length=255, help_text = 'Name des Betreibers', blank=False)
    address = models.TextField("address of bioengineering facility", help_text = 'Anschrift der gentechnischen Anlage', blank=False)
    name_biosafety_officer = models.CharField("name of the biosafety officer", max_length=255, help_text = 'Name des Beauftragten für die Biologische Sicherheit', blank=False)

    s1_approval_file_num = models.CharField("file number for S1 approval", max_length=255, help_text = 'e.g. 21-29,8 B 56.01; TgbNr.: 8/29,0/11/36',blank=False)
    s1_approval_date = models.DateField("S1 approval date", blank=False, null=True)
    s2_approval_file_num = models.CharField("file number for S2 approval", max_length=255, help_text = 'e.g. 29,8 B 56.02:21; TgbNr.: 8/29,0/13/46', blank=False)
    s2_approval_date = models.DateField("S2 approval date", blank=False, null=True)

    class Meta:
        '''Set a custom name to be used throughout the admin pages'''
        
        verbose_name = 'header'
        verbose_name_plural = 'headers'

    def __str__(self):
        '''Set what to show as an object's unicode attribute, in this case
        it is just the ID of the object, but it could be its name'''
        
        return str(self.operator)