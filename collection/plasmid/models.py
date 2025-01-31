import random
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models

from common.models import (
    DocFileMixin,
    DownloadFileNameMixin,
    SaveWithoutHistoricalRecord,
)
from formz.models import ZkbsPlasmid

from ..shared.models import (
    ApprovalFieldsMixin,
    CommonCollectionModelPropertiesMixin,
    FormZFieldsMixin,
    HistoryFieldMixin,
    MapFileChecPropertieskMixin,
    OwnershipFieldsMixin,
)

FILE_SIZE_LIMIT_MB = getattr(settings, "FILE_SIZE_LIMIT_MB", 2)


PLASMID_AS_ECOLI_STOCK = getattr(settings, "PLASMID_AS_ECOLI_STOCK", False)


class Plasmid(
    SaveWithoutHistoricalRecord,
    DownloadFileNameMixin,
    CommonCollectionModelPropertiesMixin,
    FormZFieldsMixin,
    HistoryFieldMixin,
    MapFileChecPropertieskMixin,
    ApprovalFieldsMixin,
    OwnershipFieldsMixin,
    models.Model,
):
    class Meta:
        verbose_name = "plasmid"
        verbose_name_plural = "plasmids"

    _model_abbreviation = "p"
    _model_upload_to = "collection/plasmid/"
    german_name = "Plasmid"

    name = models.CharField("name", max_length=255, unique=True, blank=False)
    other_name = models.CharField("other name", max_length=255, blank=True)
    parent_vector = models.ForeignKey(
        "self",
        verbose_name="parent vector",
        related_name="%(class)s_parent_vector",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    old_parent_vector = models.CharField(
        "orig. parent vector field",
        help_text="Use only when strictly necessary",
        max_length=255,
        blank=True,
    )
    selection = models.CharField("selection", max_length=50, blank=False)
    us_e = models.CharField("use", max_length=255, blank=True)
    construction_feature = models.TextField("construction/features", blank=True)
    received_from = models.CharField("received from", max_length=255, blank=True)
    note = models.CharField("note", max_length=300, blank=True)
    reference = models.CharField("reference", max_length=255, blank=True)
    map = models.FileField(
        "Map (.dna)",
        help_text=f"only SnapGene .dna files, max. {FILE_SIZE_LIMIT_MB} MB",
        upload_to=_model_upload_to + "dna/",
        blank=True,
    )
    map_png = models.ImageField(
        "Map image", upload_to=_model_upload_to + "png/", blank=True
    )
    map_gbk = models.FileField(
        "Map (.gbk)",
        upload_to=_model_upload_to + "gbk/",
        help_text=f"only .gbk or .gb files, max. {FILE_SIZE_LIMIT_MB} MB",
        blank=True,
    )
    vector_zkbs = models.ForeignKey(
        ZkbsPlasmid,
        verbose_name="ZKBS database vector",
        on_delete=models.PROTECT,
        blank=False,
        null=True,
        help_text="The backbone of the plasmid, from the ZKBS database. If not applicable, "
        'choose none. <a href="/formz/zkbsplasmid/" target="_blank">View all</a>',
    )
    formz_ecoli_strains = models.ManyToManyField(
        "EColiStrain",
        verbose_name="e. coli strains",
        related_name="%(class)s_ecoli_strains",
        blank=False,
    )

    history_formz_ecoli_strains = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="e. coli strains",
        blank=True,
        null=True,
        default=list,
    )
    history_documents = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="documents",
        blank=True,
        null=True,
        default=list,
    )

    def __str__(self):
        return f"{self.id} - {self.name}"

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        # If destroyed date not present, automatically set it if a plasmid is
        # not kept as E. coli stock
        if not PLASMID_AS_ECOLI_STOCK and not self.destroyed_date:
            self.destroyed_date = datetime.now().date() + timedelta(
                days=random.randint(7, 21)
            )

        super().save(force_insert, force_update, using, update_fields)

    @property
    def all_plasmids_with_maps(self):
        if self.map:
            return [self]
        else:
            return []


class PlasmidDoc(DocFileMixin):
    class Meta:
        verbose_name = "plasmid document"

    _inline_foreignkey_fieldname = "plasmid"
    _mixin_props = {
        "destination_dir": "collection/plasmiddoc/",
        "file_prefix": "pDoc",
        "parent_field_name": "plasmid",
    }

    plasmid = models.ForeignKey(Plasmid, on_delete=models.PROTECT)
