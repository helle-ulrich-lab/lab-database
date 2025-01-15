import random
from datetime import timedelta

from django.db import models

from collection.models.shared import (
    ApprovalFieldsMixin,
    CommonCollectionModelPropertiesMixin,
    FormZFieldsMixin,
    HistoryDocFieldMixin,
    HistoryFieldMixin,
    HistoryPlasmidsFieldsMixin,
    OwnershipFieldsMixin,
)
from common.models import DocFileMixin, SaveWithoutHistoricalRecord
from formz.models import FormZProject, Species, ZkbsCellLine

################################################
#                   Cell line                  #
################################################


class CellLine(
    SaveWithoutHistoricalRecord,
    CommonCollectionModelPropertiesMixin,
    FormZFieldsMixin,
    HistoryPlasmidsFieldsMixin,
    HistoryDocFieldMixin,
    HistoryFieldMixin,
    ApprovalFieldsMixin,
    OwnershipFieldsMixin,
    models.Model,
):
    class Meta:
        verbose_name = "cell line"
        verbose_name_plural = "cell lines"

    _model_abbreviation = "cl"
    _related_name_base = "cellline"

    name = models.CharField("name", max_length=255, unique=True, blank=False)
    box_name = models.CharField("box", max_length=255, blank=False)
    alternative_name = models.CharField("alternative name", max_length=255, blank=True)
    parental_line_old = models.CharField(
        "parental cell line", max_length=255, blank=False
    )
    parental_line = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        verbose_name="parental line",
        blank=True,
        null=True,
    )
    organism = models.ForeignKey(
        Species,
        verbose_name="organism",
        on_delete=models.PROTECT,
        null=True,
        blank=False,
    )
    cell_type_tissue = models.CharField("cell type/tissue", max_length=255, blank=True)
    culture_type = models.CharField("culture type", max_length=255, blank=True)
    growth_condition = models.CharField("growth conditions", max_length=255, blank=True)
    freezing_medium = models.CharField("freezing medium", max_length=255, blank=True)
    received_from = models.CharField("received from", max_length=255, blank=True)
    description_comment = models.TextField("description/comments", blank=True)
    s2_work = models.BooleanField(
        "Used for S2 work?",
        default=False,
        help_text="Check, for example, for a cell line created by lentiviral trunsdunction",
    )

    integrated_plasmids = models.ManyToManyField(
        "Plasmid", related_name="%(class)s_integrated_plasmids", blank=True
    )
    episomal_plasmids = models.ManyToManyField(
        "Plasmid",
        related_name="%(class)s_episomal_plasmids",
        blank=True,
        through="CellLineEpisomalPlasmid",
    )

    zkbs_cell_line = models.ForeignKey(
        ZkbsCellLine,
        verbose_name="ZKBS database cell line",
        on_delete=models.PROTECT,
        null=True,
        blank=False,
        help_text='If not applicable, choose none. <a href="/formz/zkbscellline/" '
        'target="_blank">View all</a>',
    )

    history_cassette_plasmids = None
    history_all_plasmids_in_stocked_strain = None

    def __str__(self):
        return f"{self.id} - {self.name}"

    @property
    def all_instock_plasmids(self):
        all_plasmids = self.integrated_plasmids.all().distinct().order_by("id")
        return all_plasmids

    @property
    def all_transient_episomal_plasmids(self):
        all_plasmids = (
            self.celllineepisomalplasmid_set.filter(s2_work_episomal_plasmid=False)
            .distinct()
            .order_by("plasmid__id")
        )
        return all_plasmids

    @property
    def all_plasmids_with_maps(self):
        return (
            (self.integrated_plasmids.all() | self.episomal_plasmids.all())
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
    def plasmids_in_model(self):
        return self.all_instock_plasmids.order_by("id").values_list("id", flat=True)


################################################
#          Cell line Episomal Plasmid          #
################################################


class CellLineEpisomalPlasmid(models.Model):
    _inline_foreignkey_fieldname = "cell_line"

    cell_line = models.ForeignKey(CellLine, on_delete=models.PROTECT)
    plasmid = models.ForeignKey(
        "Plasmid", verbose_name="Plasmid", on_delete=models.PROTECT
    )
    formz_projects = models.ManyToManyField(
        FormZProject, related_name="%(class)s_projects", blank=True
    )
    s2_work_episomal_plasmid = models.BooleanField(
        "Used for S2 work?",
        help_text="Check, for example, for lentiviral packaging plasmids",
        default=False,
    )
    created_date = models.DateField("created", blank=False, null=True)
    destroyed_date = models.DateField("destroyed", blank=True, null=True)

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        # If destroyed date not present and plasmid not in stocked strain, automatically set destroyed date
        if not self.destroyed_date and self.created_date:
            if self.s2_work_episomal_plasmid:
                self.destroyed_date = self.created_date + timedelta(days=2)
            else:
                self.destroyed_date = self.created_date + timedelta(
                    days=random.randint(7, 28)
                )

        super().save(force_insert, force_update, using, update_fields)

    def is_highlighted(self):
        return self.s2_work_episomal_plasmid


################################################
#                 Cell line Doc                #
################################################

CELL_LINE_DOC_TYPE_CHOICES = (
    ("virus", "Virus test"),
    ("mycoplasma", "Mycoplasma test"),
    ("fingerprint", "Fingerprinting"),
    ("other", "Other"),
)


class CellLineDoc(DocFileMixin):
    class Meta:
        verbose_name = "cell line document"

    _inline_foreignkey_fieldname = "cell_line"
    _mixin_props = {
        "destination_dir": "collection/celllinedoc/",
        "file_prefix": "clDoc",
        "parent_field_name": "cell_line",
    }

    description = models.CharField(
        "doc type", max_length=255, choices=CELL_LINE_DOC_TYPE_CHOICES, blank=False
    )
    date_of_test = models.DateField("date of test", blank=False, null=True)
    cell_line = models.ForeignKey(CellLine, on_delete=models.PROTECT)
