# -*- coding: utf-8 -*-

from __future__ import unicode_literals

#################################################
#    DJANGO 'CORE' FUNCTIONALITIES IMPORTS      #
#################################################

from django.db import models
from django.contrib.auth.models import User
from django.utils.encoding import force_unicode
from django.forms import ValidationError

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType

#################################################
#        ADDED FUNCTIONALITIES IMPORTS          #
#################################################

from simple_history.models import HistoricalRecords

#################################################
#                OTHER IMPORTS                  #
#################################################

import os.path
import time

#################################################
#              ARCHE NOAH MODEL                 #
#################################################

class ArcheNoahAnimal (models.Model):
    '''Special model to collect objects (items) from other models
    that have been added to the Arche Noah backup'''

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    class Meta:
        verbose_name = 'Arche Noah item'
        verbose_name_plural = 'Arche Noah items'

#################################################
#         SA. CEREVISIAE STRAIN MODEL           #
#################################################

class SaCerevisiaeStrain (models.Model):
    name = models.CharField("Name", max_length = 255, blank=False)
    relevant_genotype = models.CharField("Relevant Genotype", max_length = 255, blank=False)
    mating_type = models.CharField("Mating Type", max_length = 20, blank=True)
    chromosomal_genotype = models.TextField("Chromosomal Genotype", blank=True)
    parental_strain = models.CharField("Parental Strain", max_length = 255, blank=True)
    construction = models.TextField("Construction", blank=True)
    modification = models.CharField("Modification", max_length = 255, blank=True)
    plasmids = models.CharField("Plasmids", max_length = 255, blank=True)
    selection = models.CharField("Selection", max_length = 255, blank=True)
    phenotype = models.CharField("Phenotype", max_length = 255, blank=True)
    background = models.CharField("Background", max_length = 255, blank=True)
    received_from = models.CharField("Received from", max_length = 255, blank=True)
    us_e = models.CharField("Use", max_length = 255, blank=True)
    note = models.CharField("Note", max_length = 255, blank=True)
    reference = models.CharField("Reference", max_length = 255, blank=True)
    
    created_date_time = models.DateTimeField("Created", auto_now_add=True)
    last_changed_date_time = models.DateTimeField("Last Changed", auto_now=True)
    created_by = models.ForeignKey(User)
    history = HistoricalRecords()
    
    class Meta:
        '''Set a custom name to be used throughout the admin pages'''
        
        verbose_name = 'strain - Sa. cerevisiae'
        verbose_name_plural = 'strains - Sa. cerevisiae'
    
    def __unicode__(self):
        '''Set what to show as an object's unicode attribute, in this case
        it is just the ID of the object, but it could be its name'''
        
        return str(self.id)

#################################################
#                PLASMID MODEL                  #
#################################################

class HuPlasmid (models.Model):
    name = models.CharField("Name", max_length = 255, blank=False)
    other_name = models.CharField("Other Name", max_length = 255, blank=True)
    parent_vector = models.CharField("Parent Vector", max_length = 255, blank=True)
    selection = models.CharField("Selection", max_length = 50, blank=False)
    us_e = models.CharField("Use", max_length = 255, blank=True)
    construction_feature = models.TextField("Construction/Features", blank=True)
    received_from = models.CharField("Received from", max_length = 255, blank=True)
    note = models.CharField("Note", max_length = 300, blank=True)
    reference = models.CharField("Reference", max_length = 255, blank=True)
    plasmid_map = models.FileField("Plasmid Map (max. 2 MB)", upload_to="temp/", blank=True)
    
    created_date_time = models.DateTimeField("Created", auto_now_add=True)
    last_changed_date_time = models.DateTimeField("Last Changed", auto_now=True)
    created_by = models.ForeignKey(User)
    history = HistoricalRecords()
    
    class Meta:
        '''Set a custom name to be used throughout the admin pages'''
        
        verbose_name = 'plasmid'
        verbose_name_plural = 'plasmids'

    RENAME_FILES = {
            'plasmid_map': {'dest': 'plasmids/', 'keep_ext': True}
        }

    def save(self, force_insert=False, force_update=False):
        '''Override default save method to rename a plasmid map 
        of any given name to pHUX_date-uploaded_time-uploaded.yyy,
        after the corresponding entry has been created'''
        
        rename_files = getattr(self, 'RENAME_FILES', None)
        if rename_files:
            super(HuPlasmid, self).save(force_insert, force_update)
            force_insert, force_update = False, True
            for field_name, options in rename_files.iteritems():
                field = getattr(self, field_name)
                if field:
                    file_name = force_unicode(field)
                    name, ext = os.path.splitext(file_name)
                    keep_ext = options.get('keep_ext', True)
                    final_dest = options['dest']
                    if callable(final_dest):
                        final_name = final_dest(self, file_name)
                    else:
                        final_name = os.path.join(final_dest, "pHU" + '%s' % (self.pk,) + "_" + time.strftime("%Y%m%d") + "_" + time.strftime("%H%M%S"))
                        if keep_ext:
                            final_name += ext
                    if file_name != final_name:
                        field.storage.delete(final_name)
                        field.storage.save(final_name, field)
                        field.close()
                        field.storage.delete(file_name)
                        setattr(self, field_name, final_name)
        super(HuPlasmid, self).save(force_insert, force_update)

    # Check if file is bigger than 2 MB
    def clean(self): 
        errors = []
        
        limit = 2 * 1024 * 1024
        if self.plasmid_map:
            if self.plasmid_map.size > limit:
                errors.append(ValidationError('Plasmid map too large. Size cannot exceed 2 MB.'))
        
            try:
                plasmid_map_ext = self.plasmid_map.name.split('.')[-1].lower()
            except:
                plasmid_map_ext = None
            if plasmid_map_ext == None or plasmid_map_ext != 'dna':
                errors.append(ValidationError('Invalid file format. Please select a valid SnapGene .dna file'))

        if len(errors) > 0:
            raise ValidationError(errors)

    def __unicode__(self):
        return str(self.id)

#################################################
#                 OLIGO MODEL                   #
#################################################

class Oligo (models.Model):
    name = models.CharField("Name", max_length = 255, unique = True, blank=False)
    sequence = models.CharField("Sequence", max_length = 255, unique = True, blank=False)
    length = models.SmallIntegerField("Length", null=True, blank=True)
    us_e = models.CharField("Use", max_length = 255, blank=True)
    gene = models.CharField("Gene", max_length = 255, blank=True)
    restriction_site = models.CharField("Restriction sites", max_length = 255, blank=True)
    description = models.TextField("Description", blank=True)
    comment = models.CharField("Comments", max_length = 255, blank=True)
    
    created_date_time = models.DateTimeField("Created", auto_now_add=True)
    last_changed_date_time = models.DateTimeField("Last Changed", auto_now=True)
    created_by = models.ForeignKey(User)
    history = HistoricalRecords()
    
    def __unicode__(self):
       return str(self.id)

    # Automatically capitalize the sequence of an oligo and remove all white spaces
    # from it. Also set the lenght of the oligo  
    def save(self, force_insert=False, force_update=False):
        upper_sequence = self.sequence.upper()
        self.sequence = "".join(upper_sequence.split())
        self.length = len(self.sequence)
        super(Oligo, self).save(force_insert, force_update)

#################################################
#            SC. POMBE STRAIN MODEL             #
#################################################

class ScPombeStrain (models.Model):
    box_number = models.SmallIntegerField("Box number", blank=False)
    parental_strain = models.CharField("Parental strains", max_length = 255, blank=True)
    mating_type = models.CharField("Mating Type", max_length = 20, blank=True)
    auxotrophic_marker = models.CharField("Auxotrophic markers", max_length = 255, blank=True)
    genotype = models.TextField("Genotype", blank=False)
    phenotype = models.CharField("Phenotype", max_length = 255, blank=True)
    received_from = models.CharField("Received from", max_length = 255, blank=True)
    comment = models.CharField("Comments", max_length = 300, blank=True)
    
    created_date_time = models.DateTimeField("Created", auto_now_add=True)
    last_changed_date_time = models.DateTimeField("Last Changed", auto_now=True)
    created_by = models.ForeignKey(User)
    history = HistoricalRecords()
    
    class Meta:
        verbose_name = 'strain - Sc. pombe'
        verbose_name_plural = 'strains - Sc. pombe'
    
    def __unicode__(self):
        return str(self.id)

#################################################
#                NZ PLASMID MODEL               #
#################################################

# Subclass to rename a plasmid map of any given name as pNZX_date-uploaded_time-uploaded.yyy
class NzPlasmid (models.Model):
    name = models.CharField("Name", max_length = 255, blank=False)
    other_name = models.CharField("Other Name", max_length = 255, blank=True)
    parent_vector = models.CharField("Parent Vector", max_length = 255, blank=True)
    selection = models.CharField("Selection", max_length = 50, blank=False)
    us_e = models.CharField("Use", max_length = 255, blank=True)
    construction_feature = models.TextField("Construction/Features", blank=True)
    received_from = models.CharField("Received from", max_length = 255, blank=True)
    note = models.CharField("Note", max_length = 300, blank=True)
    reference = models.CharField("Reference", max_length = 255, blank=True)
    plasmid_map = models.FileField("Plasmid Map (max. 2 MB)", upload_to="temp/", blank=True)
    
    created_date_time = models.DateTimeField("Created", auto_now_add=True)
    last_changed_date_time = models.DateTimeField("Last Changed", auto_now=True)
    created_by = models.ForeignKey(User)
    history = HistoricalRecords()

    RENAME_FILES = {
            'plasmid_map': {'dest': 'nz_plasmids/', 'keep_ext': True}
        }
     
    def save(self, force_insert=False, force_update=False):
        rename_files = getattr(self, 'RENAME_FILES', None)
        if rename_files:
            super(NzPlasmid, self).save(force_insert, force_update)
            force_insert, force_update = False, True
            for field_name, options in rename_files.iteritems():
                field = getattr(self, field_name)
                if field:
                    file_name = force_unicode(field)
                    name, ext = os.path.splitext(file_name)
                    keep_ext = options.get('keep_ext', True)
                    final_dest = options['dest']
                    if callable(final_dest):
                        final_name = final_dest(self, file_name)
                    else:
                        final_name = os.path.join(final_dest, "pNZ" + '%s' % (self.pk,) + "_" + time.strftime("%Y%m%d") + "_" + time.strftime("%H%M%S"))
                        if keep_ext:
                            final_name += ext
                    if file_name != final_name:
                        field.storage.delete(final_name)
                        field.storage.save(final_name, field)
                        field.close()
                        field.storage.delete(file_name)
                        setattr(self, field_name, final_name)
        super(NzPlasmid, self).save(force_insert, force_update)

    def clean(self): 
        errors = []
        
        limit = 2 * 1024 * 1024
        if self.plasmid_map:
            if self.plasmid_map.size > limit:
                errors.append(ValidationError('Plasmid map too large. Size cannot exceed 2 MB.'))
        
            try:
                plasmid_map_ext = self.plasmid_map.name.split('.')[-1].lower()
            except:
                plasmid_map_ext = None
            if plasmid_map_ext == None or plasmid_map_ext != 'dna':
                errors.append(ValidationError('Invalid file format. Please select a valid SnapGene .dna file'))

        if len(errors) > 0:
            raise ValidationError(errors)
    
    class Meta:
        verbose_name = "nicola's plasmid"
        verbose_name_plural = "nicola's plasmids"
        
    def __unicode__(self):
        return str(self.id)

#################################################
#              E. COLI STRAIN MODEL             #
#################################################

class EColiStrain (models.Model):
    name = models.CharField("Name", max_length = 255, blank=False)
    resistance = models.CharField("Resistance", max_length = 255, blank=True)
    genotype = models.TextField("Genotype", blank=True)
    supplier = models.CharField("Supplier", max_length = 255, blank=True)
    us_e = models.CharField("Use", max_length = 255, choices=(('Cloning', 'Cloning'),('Expression', 'Expression'),('Other', 'Other'),))
    purpose = models.TextField("Purpose", blank=True)
    note =  models.CharField("Note", max_length = 255, blank=True)
    
    created_date_time = models.DateTimeField("Created", auto_now_add=True)
    last_changed_date_time = models.DateTimeField("Last Changed", auto_now=True)
    created_by = models.ForeignKey(User)
    history = HistoricalRecords()
    
    class Meta:
        verbose_name = 'strain - E. coli'
        verbose_name_plural = 'strains - E. coli'
        
    def __unicode__(self):
       return str(self.id)

################################################
#         MAMMALIAN CELL LINE MODEL            #
################################################

def parental_line_choices():
    MammalianLine.objects.all()

class MammalianLine (models.Model):
    name = models.CharField("Name", max_length = 255, blank=False)
    box_name = models.CharField("Box", max_length = 255, blank=False)
    alternative_name = models.CharField("Alternative name", max_length = 255, blank=True)
    parental_line = models.CharField("Parental cell line", max_length = 255, blank=False)
    organism = models.CharField("Organism", max_length = 20, blank=True)
    cell_type_tissue = models.CharField("Cell type/Tissue", max_length = 255, blank=True)
    culture_type = models.CharField("Culture type", max_length = 255, blank=True)
    growth_condition = models.CharField("Growth conditions", max_length = 255, blank=True)
    freezing_medium = models.CharField("Freezing medium", max_length = 255, blank=True)
    received_from = models.CharField("Received from", max_length = 255, blank=True)
    description_comment = models.TextField("Description/Comments", max_length = 300, blank=True)
    
    created_date_time = models.DateTimeField("Created", auto_now_add=True)
    last_changed_date_time = models.DateTimeField("Last Changed", auto_now=True)
    created_by = models.ForeignKey(User)
    history = HistoricalRecords()
    
    class Meta:
        verbose_name = 'mammmalian cell line'
        verbose_name_plural = 'mammmalian cell lines'
    
    def __unicode__(self):
        return str(self.id)

class MammalianLineDoc(models.Model):
    name = models.FileField("File name", upload_to="temp/", blank=False)
    typ_e = models.CharField("Doc Type", max_length=255, choices=[["virus", "Virus test"], ["mycoplasma", "Mycoplasma test"], ["fingerprint", "Fingerprinting"], ["other", "Other"]], blank=False)
    date_of_test = models.DateField("Date of test", blank=False)
    mammalian_line = models.ForeignKey(MammalianLine)
    
    created_date_time = models.DateTimeField("Created", auto_now_add=True)
    last_changed_date_time = models.DateTimeField("Last Changed", auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'mammalian cell line document'
    
    def __unicode__(self):
         return str(self.id)

    RENAME_FILES = {
            'name': {'dest': 'mammalian_cell_line_docs/', 'keep_ext': True}
        }

    def save(self, force_insert=False, force_update=False):
        rename_files = getattr(self, 'RENAME_FILES', None)
        if rename_files:
            super(MammalianLineDoc, self).save(force_insert, force_update)
            force_insert, force_update = False, True
            for field_name, options in rename_files.iteritems():
                field = getattr(self, field_name)
                if field:
                    file_name = force_unicode(field)
                    name, ext = os.path.splitext(file_name)
                    keep_ext = options.get('keep_ext', True)
                    final_dest = options['dest']
                    if callable(final_dest):
                        final_name = final_dest(self, file_name)
                    else:
                        final_name = os.path.join(final_dest, "mclHU" + str(self.mammalian_line.id) + "_" + self.typ_e + "_" + time.strftime("%Y%m%d") + "_" + time.strftime("%H%M%S") + "_" + str(self.id))
                        if keep_ext:
                            final_name += ext
                    if file_name != final_name:
                        field.storage.delete(final_name)
                        field.storage.save(final_name, field)
                        field.close()
                        field.storage.delete(file_name)
                        setattr(self, field_name, final_name)
        super(MammalianLineDoc, self).save(force_insert, force_update)

    def clean(self): 
        errors = []
        
        limit = 2 * 1024 * 1024
        if self.name:
            if self.name.size > limit:
                errors.append(ValidationError('File too large. Size cannot exceed 2 MB.'))
            try:
                file_ext = self.name.name.split('.')[-1].lower()
            except:
                errors.append(ValidationError('Invalid file format. File does not have an extension'))

        if len(errors) > 0:
            raise ValidationError(errors)

#################################################
#                ANTIBODY MODEL                 #
#################################################

# Subclass to rename am antibody information sheet as ab_info_X.yyy
class Antibody (models.Model):
    name = models.CharField("Name", max_length = 255, blank=False)
    species_isotype = models.CharField("Species/Isotype", max_length = 255, blank=False)
    clone = models.CharField("Clone", max_length = 255, blank=True)
    received_from = models.CharField("Receieved from", max_length = 255, blank=True)
    catalogue_number = models.CharField("Catalogue number", max_length = 255, blank=True)
    l_ocation = models.CharField("Location", max_length = 255, blank=True)
    a_pplication = models.CharField("Application", max_length = 255, blank=True)
    description_comment = models.TextField("Description/Comments", max_length = 300, blank=True)
    info_sheet = models.FileField("Info sheet (max. 2 MB)", upload_to="temp/", blank=True)

    created_date_time = models.DateTimeField("Created", auto_now_add=True)
    last_changed_date_time = models.DateTimeField("Last Changed", auto_now=True)
    created_by = models.ForeignKey(User)
    history = HistoricalRecords()
    
    arche_noah_choice = models.BooleanField("Added to Arche Noah?", default=False)
    arche_noah_relationship = GenericRelation(ArcheNoahAnimal)
    
    RENAME_FILES = {
            'info_sheet': {'dest': 'antibody_info_sheets/', 'keep_ext': True}
        }

    def save(self, force_insert=False, force_update=False):
        rename_files = getattr(self, 'RENAME_FILES', None)
        if rename_files:
            super(Antibody, self).save(force_insert, force_update)
            force_insert, force_update = False, True
            for field_name, options in rename_files.iteritems():
                field = getattr(self, field_name)
                if field:
                    file_name = force_unicode(field)
                    name, ext = os.path.splitext(file_name)
                    keep_ext = options.get('keep_ext', True)
                    final_dest = options['dest']
                    if callable(final_dest):
                        final_name = final_dest(self, file_name)
                    else:
                        final_name = os.path.join(final_dest, "ab_info_" + '%s' % (self.pk,))
                        if keep_ext:
                            final_name += ext
                    if file_name != final_name:
                        field.storage.delete(final_name)
                        field.storage.save(final_name, field)
                        field.close()
                        field.storage.delete(file_name)
                        setattr(self, field_name, final_name)
        super(Antibody, self).save(force_insert, force_update)

    def clean(self):
        errors = []
        
        limit = 2 * 1024 * 1024
        if self.info_sheet:
            if self.info_sheet.size > limit:
                errors.append(ValidationError('File too large. Size cannot exceed 2 MB.'))
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
    
    def __unicode__(self):
        return str(self.id)