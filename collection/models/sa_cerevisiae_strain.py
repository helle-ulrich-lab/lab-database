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
#             S. cerevisiae strain             #
################################################

CEREVISIAE_MATING_TYPE_CHOICES = (
    ("a", "a"),
    ("alpha", "alpha"),
    ("unknown", "unknown"),
    ("a/a", "a/a"),
    ("alpha/alpha", "alpha/alpha"),
    ("a/alpha", "a/alpha"),
    ("other", "other"),
)


class SaCerevisiaeStrain(
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
        verbose_name = "strain - Sa. cerevisiae"
        verbose_name_plural = "strains - Sa. cerevisiae"

    _model_abbreviation = "sc"

    name = models.CharField("name", max_length=255, blank=False)
    relevant_genotype = models.CharField(
        "relevant genotype", max_length=255, blank=False
    )
    mating_type = models.CharField(
        "mating type", choices=CEREVISIAE_MATING_TYPE_CHOICES, max_length=20, blank=True
    )
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
    parental_strain = models.CharField(
        "parental strain",
        help_text="Use only when 'Parent 1' does not apply",
        max_length=255,
        blank=True,
    )
    construction = models.TextField("construction", blank=True)
    modification = models.CharField("modification", max_length=255, blank=True)
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
        through="SaCerevisiaeStrainEpisomalPlasmid",
    )
    plasmids = models.CharField(
        "plasmids",
        max_length=255,
        help_text="Use only when the other plasmid fields do not apply",
        blank=True,
    )
    selection = models.CharField("selection", max_length=255, blank=True)
    phenotype = models.CharField("phenotype", max_length=255, blank=True)
    background = models.CharField("background", max_length=255, blank=True)
    received_from = models.CharField("received from", max_length=255, blank=True)
    us_e = models.CharField("use", max_length=255, blank=True)
    note = models.CharField("note", max_length=255, blank=True)
    reference = models.CharField("reference", max_length=255, blank=True)

    history_documents = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="documents",
        blank=True,
        null=True,
        default=list,
    )

    def __str__(self):
        return f"{self.id} - {self.name}"

    @property
    def all_instock_plasmids(self):
        """Returns all plasmids present in the stocked organism"""

        all_plasmids = (
            (
                self.integrated_plasmids.all()
                | self.cassette_plasmids.all()
                | self.episomal_plasmids.filter(
                    sacerevisiaestrainepisomalplasmid__present_in_stocked_strain=True
                )
            )
            .distinct()
            .order_by("id")
        )
        return all_plasmids

    @property
    def all_transient_episomal_plasmids(self):
        """Returns all transiently transformed episomal plasmids"""

        all_plasmids = (
            self.sacerevisiaestrainepisomalplasmid_set.filter(
                present_in_stocked_strain=False
            )
            .distinct()
            .order_by("plasmid__id")
        )
        return all_plasmids

    @property
    def all_plasmids_with_maps(self):
        """Returns all plasmids"""
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


################################################
#     S. cerevisiae strain Episomal Plasmid    #
################################################


class SaCerevisiaeStrainEpisomalPlasmid(models.Model):

    _inline_foreignkey_fieldname = "sacerevisiae_strain"

    sacerevisiae_strain = models.ForeignKey(
        SaCerevisiaeStrain, on_delete=models.PROTECT
    )
    plasmid = models.ForeignKey(
        "Plasmid", verbose_name="Plasmid", on_delete=models.PROTECT
    )
    present_in_stocked_strain = models.BooleanField(
        "present in -80° C stock?",
        help_text="Check, if the culture you stocked for the -80° C "
        "collection contains an episomal plasmid. Leave unchecked, if you simply want to record that you have "
        "transiently transformed this strain with an episomal plasmid",
        default=False,
    )
    formz_projects = models.ManyToManyField(
        FormZProject, related_name="cerevisiae_episomal_plasmid_projects", blank=True
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

        # If destroyed date not present and plasmid not in stocked strain, automatically set destroyed date
        if self.present_in_stocked_strain:
            self.created_date = None
            self.destroyed_date = None
        else:
            if not self.destroyed_date and self.created_date:
                self.destroyed_date = self.created_date + timedelta(
                    days=random.randint(7, 28)
                )

        super(SaCerevisiaeStrainEpisomalPlasmid, self).save(
            force_insert, force_update, using, update_fields
        )

    def is_highlighted(self):
        return self.present_in_stocked_strain


################################################
#           S. cerevisiae strain Doc           #
################################################


class SaCerevisiaeStrainDoc(DocFileMixin):

    _inline_foreignkey_fieldname = "sacerevisiae_strain"
    _mixin_props = {
        "destination_dir": "collection/sacerevisiaestraindoc/",
        "file_prefix": "scDoc",
        "parent_field_name": "sacerevisiae_strain",
    }

    sacerevisiae_strain = models.ForeignKey(
        SaCerevisiaeStrain, on_delete=models.PROTECT
    )

    class Meta:
        verbose_name = "sa. cerevisiae strain document"
