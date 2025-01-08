import random
from datetime import timedelta

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.forms import ValidationError

from collection.models.shared import (
    ApprovalFieldsMixin,
    CommonCollectionModelPropertiesMixin,
    FormZFieldsMixin,
    HistoryFieldMixin,
    HistoryPlasmidsFieldsMixin,
    OwnershipFieldsMixin,
)
from common.models import DocFileMixin, SaveWithoutHistoricalRecord
from formz.models import FormZProject

################################################
#                S. pombe strain               #
################################################


class ScPombeStrain(
    SaveWithoutHistoricalRecord,
    CommonCollectionModelPropertiesMixin,
    FormZFieldsMixin,
    HistoryPlasmidsFieldsMixin,
    HistoryFieldMixin,
    ApprovalFieldsMixin,
    OwnershipFieldsMixin,
    models.Model,
):
    class Meta:
        verbose_name = "strain - Sc. pombe"
        verbose_name_plural = "strains - Sc. pombe"

    _model_abbreviation = "sp"

    box_number = models.SmallIntegerField("box number", blank=False)
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
    parental_strain = models.CharField("parental strains", max_length=255, blank=True)
    mating_type = models.CharField("mating type", max_length=20, blank=True)
    auxotrophic_marker = models.CharField(
        "auxotrophic markers", max_length=255, blank=True
    )
    name = models.TextField("genotype", blank=False)
    phenotype = models.CharField("phenotype", max_length=255, blank=True)
    received_from = models.CharField("received from", max_length=255, blank=True)
    comment = models.CharField("comments", max_length=300, blank=True)
    integrated_plasmids = models.ManyToManyField(
        "Plasmid", related_name="%(class)s_integrated_plasmids", blank=True
    )
    cassette_plasmids = models.ManyToManyField(
        "Plasmid",
        related_name="%(class)s_cassette_plasmids",
        help_text="Tagging and knock out plasmids",
        blank=True,
    )
    episomal_plasmids = models.ManyToManyField(
        "Plasmid",
        related_name="%(class)s_episomal_plasmids",
        blank=True,
        through="ScPombeStrainEpisomalPlasmid",
    )

    history_documents = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="documents",
        blank=True,
        null=True,
        default=list,
    )

    def __str__(self):
        return f"{self.id} - {self.genotype}"

    @property
    def all_instock_plasmids(self):
        all_plasmids = (
            (
                self.integrated_plasmids.all()
                | self.cassette_plasmids.all()
                | self.episomal_plasmids.all()
            )
            .distinct()
            .order_by("id")
        )
        return all_plasmids

    @property
    def all_transient_episomal_plasmids(self):
        all_plasmids = (
            self.scpombestrainepisomalplasmid_set.filter(
                present_in_stocked_strain=False
            )
            .distinct()
            .order_by("plasmid__id")
        )
        return all_plasmids

    @property
    def all_plasmids_with_maps(self):
        return (
            (
                self.integrated_plasmids.all()
                | self.episomal_plasmids.all()
                | self.cassette_plasmids.all()
            )
            .distinct()
            .exclude(map="")
            .order_by("id")
        )

    @property
    def all_uncommon_formz_elements(self):
        elements = super().all_uncommon_formz_elements
        all_plasmids = self.all_instock_plasmids
        for pl in all_plasmids:
            elements = elements | pl.formz_elements.all()
        elements = elements.distinct().filter(common_feature=False).order_by("name")
        return elements

    @property
    def all_common_formz_elements(self):
        elements = super().all_common_formz_elements
        all_plasmids = self.all_instock_plasmids
        for pl in all_plasmids:
            elements = elements | pl.formz_elements.all()
        elements = elements.distinct().filter(common_feature=True).order_by("name")
        return elements

    @property
    def genotype(self):
        """Returns the full genotype of the strain"""

        return " ".join([e for e in [self.auxotrophic_marker, self.name] if e])


################################################
#       S. pombe strain Episomal Plasmid       #
################################################


class ScPombeStrainEpisomalPlasmid(models.Model):
    _inline_foreignkey_fieldname = "scpombe_strain"

    scpombe_strain = models.ForeignKey(ScPombeStrain, on_delete=models.PROTECT)
    plasmid = models.ForeignKey(
        "Plasmid", verbose_name="Plasmid", on_delete=models.PROTECT
    )
    present_in_stocked_strain = models.BooleanField(
        "present in -80° C stock?", default=False
    )
    formz_projects = models.ManyToManyField(
        FormZProject, related_name="%(class)s_episomal_plasmid_projects", blank=True
    )
    created_date = models.DateField("created", blank=True, null=True)
    destroyed_date = models.DateField("destroyed", blank=True, null=True)

    def clean(self):
        errors = {}

        # Check that a transiently transfected plasmid has a created date
        if not self.present_in_stocked_strain and not self.created_date:
            errors["created_date"] = errors.get("created_date", []) + [
                "Transiently tranformed episomal plasmids must have a created date"
            ]

        if errors:
            raise ValidationError(errors)

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        # If destroyed date not present and plasmid not in stocked strain,
        # automatically set destroyed date
        if self.present_in_stocked_strain:
            self.created_date = None
            self.destroyed_date = None
        else:
            if not self.destroyed_date and self.created_date:
                self.destroyed_date = self.created_date + timedelta(
                    days=random.randint(7, 28)
                )

        super().save(force_insert, force_update, using, update_fields)

    def is_highlighted(self):
        return self.present_in_stocked_strain


################################################
#              S. pombe strain Doc             #
################################################


class ScPombeStrainDoc(DocFileMixin):
    class Meta:
        verbose_name = "sc. pombe strain document"

    _inline_foreignkey_fieldname = "scpombe_strain"
    _mixin_props = {
        "destination_dir": "collection/scpombestraindoc/",
        "file_prefix": "spDoc",
        "parent_field_name": "scpombe_strain",
    }

    scpombe_strain = models.ForeignKey(ScPombeStrain, on_delete=models.PROTECT)
