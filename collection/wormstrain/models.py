from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models

from common.models import DocFileMixin, HistoryFieldMixin, SaveWithoutHistoricalRecord
from formz.models import FormZBaseElement, FormZProject, GenTechMethod

from ..oligo.models import Oligo
from ..plasmid.models import Plasmid
from ..shared.models import (
    ApprovalFieldsMixin,
    CommonCollectionModelPropertiesMixin,
    FormZFieldsMixin,
    HistoryDocFieldMixin,
    MapFileChecPropertieskMixin,
    OwnershipFieldsMixin,
)

FILE_SIZE_LIMIT_MB = getattr(settings, "FILE_SIZE_LIMIT_MB", 2)


class WormStrainAlleleDoc(DocFileMixin):
    class Meta:
        verbose_name = "worm strain allele document"

    _inline_foreignkey_fieldname = "worm_strain_allele"
    _mixin_props = {
        "destination_dir": "collection/wormstrainalleledoc/",
        "file_prefix": "waDoc",
        "parent_field_name": "worm_strain_allele",
    }

    worm_strain_allele = models.ForeignKey("WormStrainAllele", on_delete=models.PROTECT)


class WormStrainAllele(
    HistoryDocFieldMixin,
    HistoryFieldMixin,
    MapFileChecPropertieskMixin,
    OwnershipFieldsMixin,
    models.Model,
):
    class Meta:
        verbose_name = "allele - Worm"
        verbose_name_plural = "alleles - Worm"

    _model_abbreviation = "wa"
    _model_upload_to = "collection/wormstrainallele/"
    german_name = "Allel"
    _history_array_fields = {
        "history_formz_elements": FormZBaseElement,
        "history_made_with_plasmids": Plasmid,
        "history_transgene_plasmids": Plasmid,
        "history_documents": WormStrainAlleleDoc,
    }
    _history_view_ignore_fields = OwnershipFieldsMixin._history_view_ignore_fields + [
        "map_png",
        "map_gbk",
    ]

    lab_identifier = models.CharField(
        "prefix/Lab identifier",
        max_length=15,
        blank=False,
    )
    typ_e = models.CharField(
        "type",
        choices=(("t", "Transgene"), ("m", "Mutation")),
        max_length=5,
        blank=False,
    )
    transgene = models.CharField(
        "transgene", help_text="Genotype", max_length=255, blank=True
    )
    transgene_position = models.CharField(
        "transgene position", max_length=255, blank=True
    )
    transgene_plasmids = models.ManyToManyField(
        Plasmid,
        verbose_name="transgene plasmids",
        related_name="%(class)s_transgene_plasmids",
        help_text="The plasmid(s) in the transgene",
        blank=True,
    )
    mutation = models.CharField(
        "mutation", help_text="Genotype", max_length=255, blank=True
    )
    mutation_type = models.CharField("mutation type", max_length=255, blank=True)
    mutation_position = models.CharField(
        "mutation position", max_length=255, blank=True
    )
    reference_strain = models.ForeignKey(
        "WormStrain",
        verbose_name="reference strain",
        on_delete=models.PROTECT,
        related_name="%(class)s_reference_strain",
        blank=True,
        null=True,
    )
    made_by_method = models.ForeignKey(
        GenTechMethod,
        verbose_name="made by method",
        related_name="%(class)s_made_by_method",
        help_text="The method used to create the allele",
        on_delete=models.PROTECT,
        blank=False,
    )
    made_by_person = models.CharField("made by person", max_length=255, blank=False)
    made_with_plasmids = models.ManyToManyField(
        Plasmid,
        verbose_name="made with plasmids",
        help_text="The plasmid(s) used to create the transgene/mutation",
        blank=True,
    )
    notes = models.TextField("notes", blank=True)
    map = models.FileField(
        "map (.dna)",
        help_text=f"only SnapGene .dna files, max. {FILE_SIZE_LIMIT_MB} MB",
        upload_to=_model_upload_to + "dna/",
        blank=True,
    )
    map_png = models.ImageField(
        "map (.png)", upload_to=_model_upload_to + "png/", blank=True
    )
    map_gbk = models.FileField(
        "Map (.gbk)",
        upload_to=_model_upload_to + "gbk/",
        help_text=f"only .gbk or .gb files, max. {FILE_SIZE_LIMIT_MB} MB",
        blank=True,
    )
    formz_elements = models.ManyToManyField(
        FormZBaseElement,
        verbose_name="elements",
        help_text="Searching against the aliases of an element is case-sensitive. "
        '<a href="/formz/formzbaseelement/" target="_blank">View all/Change</a>',
        blank=True,
    )

    history_formz_elements = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="formz elements",
        blank=True,
        null=True,
        default=list,
    )
    history_made_with_plasmids = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="made with plasmids",
        blank=True,
        null=True,
        default=list,
    )
    history_transgene_plasmids = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="transgene plasmids",
        blank=True,
        null=True,
        default=list,
    )

    def __str__(self):
        return f"{self.lab_identifier}{self.id} - {self.name}"

    @property
    def name(self):
        return self.transgene or self.mutation

    @property
    def download_file_name(self):
        return self.__str__()

    @property
    def all_uncommon_formz_elements(self):
        elements = self.formz_elements.filter(common_feature=False).order_by("name")
        return elements

    @property
    def all_common_formz_elements(self):
        elements = self.formz_elements.filter(common_feature=True).order_by("name")
        return elements

    @property
    def plasmids_in_model(self):
        return sorted(
            list(set(self.history_transgene_plasmids + self.history_made_with_plasmids))
        )

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self.lab_identifier = self.lab_identifier.strip()
        super().save(force_insert, force_update, using, update_fields)


WORM_SPECIES_CHOICES = (
    ("celegans", "Caenorhabditis elegans"),
    ("cbriggsae", "Caenorhabditis briggsae"),
    ("cinopinata", "Caenorhabditis inopinata"),
    ("cjaponica", "Caenorhabditis japonica"),
    ("ppacificus", "Pristionchus pacificus"),
)


class WormStrainDoc(DocFileMixin):
    class Meta:
        verbose_name = "worm strain document"

    _inline_foreignkey_fieldname = "worm_strain"
    _mixin_props = {
        "destination_dir": "collection/wormstraindoc/",
        "file_prefix": "wDoc",
        "parent_field_name": "worm_strain",
    }

    worm_strain = models.ForeignKey("WormStrain", on_delete=models.PROTECT)


class WormStrain(
    SaveWithoutHistoricalRecord,
    CommonCollectionModelPropertiesMixin,
    FormZFieldsMixin,
    HistoryFieldMixin,
    HistoryDocFieldMixin,
    ApprovalFieldsMixin,
    OwnershipFieldsMixin,
    models.Model,
):
    class Meta:
        verbose_name = "strain - Worm"
        verbose_name_plural = "strains - Worm"

    _model_abbreviation = "w"
    _history_array_fields = {
        "history_integrated_dna_plasmids": Plasmid,
        "history_integrated_dna_oligos": Oligo,
        "history_formz_projects": FormZProject,
        "history_formz_gentech_methods": GenTechMethod,
        "history_formz_elements": FormZBaseElement,
        "history_genotyping_oligos": Oligo,
        "history_documents": WormStrainDoc,
        "history_alleles": WormStrainAllele,
    }
    _history_view_ignore_fields = (
        ApprovalFieldsMixin._history_view_ignore_fields
        + OwnershipFieldsMixin._history_view_ignore_fields
    )

    name = models.CharField("name", max_length=255, blank=False)
    chromosomal_genotype = models.TextField("chromosomal genotype", blank=True)
    parent_1 = models.ForeignKey(
        "self",
        verbose_name="Parent 1",
        on_delete=models.PROTECT,
        related_name="%(class)s_parent_1",
        help_text="Main parental strain",
        blank=True,
        null=True,
    )
    parent_2 = models.ForeignKey(
        "self",
        verbose_name="Parent 2",
        on_delete=models.PROTECT,
        related_name="%(class)s_parent_2",
        help_text="Only for crosses",
        blank=True,
        null=True,
    )
    construction = models.TextField("construction", blank=True)
    outcrossed = models.CharField("outcrossed", max_length=255, blank=True)
    growth_conditions = models.CharField(
        "growth conditions", max_length=255, blank=True
    )
    organism = models.CharField(
        "organism",
        choices=WORM_SPECIES_CHOICES,
        max_length=15,
        default="celegans",
        blank=False,
    )

    integrated_dna_plasmids = models.ManyToManyField(
        Plasmid,
        verbose_name="plasmids",
        related_name="%(class)s_integrated_plasmids",
        blank=True,
    )
    integrated_dna_oligos = models.ManyToManyField(
        Oligo,
        verbose_name="oligos",
        related_name="%(class)s_integrated_oligos",
        blank=True,
    )

    selection = models.CharField("selection", max_length=255, blank=True)
    phenotype = models.TextField("phenotype", blank=True)
    received_from = models.CharField("received from", max_length=255, blank=True)
    us_e = models.CharField("use", max_length=255, blank=True)
    note = models.CharField("note", max_length=255, blank=True)
    reference = models.CharField("reference", max_length=255, blank=True)
    at_cgc = models.BooleanField(
        "at CGC?", help_text="Caenorhabditis Genetics Center", blank=True, default=False
    )

    location_freezer1 = models.CharField(
        "location Freezer 1", max_length=255, blank=True
    )
    location_freezer2 = models.CharField(
        "location Freezer 2", max_length=255, blank=True
    )
    location_backup = models.CharField("location Backup", max_length=255, blank=True)
    alleles = models.ManyToManyField(
        WormStrainAllele,
        verbose_name="alleles",
        related_name="%(class)s_alleles",
        blank=True,
    )

    history_integrated_dna_plasmids = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="integrated plasmids",
        blank=True,
        null=True,
        default=list,
    )
    history_integrated_dna_oligos = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="integrated oligos",
        blank=True,
        null=True,
        default=list,
    )
    history_genotyping_oligos = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="genotyping oligos",
        blank=True,
        null=True,
        default=list,
    )
    history_alleles = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="alleles",
        blank=True,
        null=True,
        default=list,
    )

    def __str__(self):
        return f"{self.id} - {self.name}"

    @property
    def all_uncommon_formz_elements(self):
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
        elements = elements.distinct().filter(common_feature=False).order_by("name")
        return elements

    @property
    def all_common_formz_elements(self):
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
        elements = elements.distinct().filter(common_feature=True).order_by("name")
        return elements

    @property
    def all_instock_plasmids(self):
        """Returns all plasmids present in the stocked organism"""

        return self.integrated_dna_plasmids.all().distinct().order_by("id")

    @property
    def history_all_plasmids_in_stocked_strain(self):
        """Returns the IDs of the plasmids present in the stocked organism"""

        return self.all_instock_plasmids.values_list("id", flat=True)

    @property
    def all_transient_episomal_plasmids(self):
        """Returns all transiently transformed episomal plasmids"""

        return None

    @property
    def all_plasmids_with_maps(self):
        """Returns all plasmids and alleles with a map"""

        return list(
            self.alleles.all().distinct().exclude(map="").order_by("id")
        ) + list(
            self.integrated_dna_plasmids.all().distinct().exclude(map="").order_by("id")
        )

    @property
    def plasmids_in_model(self):
        return self.history_all_plasmids_in_stocked_strain

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self.name = self.name.strip()
        super().save(force_insert, force_update, using, update_fields)


class WormStrainGenotypingAssay(models.Model):
    class Meta:
        verbose_name = "worm strain genotyping assay"
        verbose_name_plural = "worm strain genotyping assays"

    _inline_foreignkey_fieldname = "worm_strain"

    worm_strain = models.ForeignKey(WormStrain, on_delete=models.PROTECT)
    locus_allele = models.CharField("locus/allele", max_length=255, blank=False)
    oligos = models.ManyToManyField(Oligo, related_name="%(class)s_oligos", blank=False)

    def __str__(self):
        return str(self.id)
