from django.contrib.postgres.fields import ArrayField
from django.db import models
from django_better_admin_arrayfield.models.fields import ArrayField as BetterArrayField

from collection.models.shared import (
    HistoryFieldMixin,
    InfoSheetMaxSizeMixin,
    OwnershipFieldsMixin,
)
from common.models import (
    DocFileMixin,
    DownloadFileNameMixin,
    SaveWithoutHistoricalRecord,
)
from formz.models import Species
from ordering.models import Order

################################################
#                     siRNA                    #
################################################


class SiRna(
    SaveWithoutHistoricalRecord,
    DownloadFileNameMixin,
    InfoSheetMaxSizeMixin,
    HistoryFieldMixin,
    OwnershipFieldsMixin,
    models.Model,
):
    class Meta:
        verbose_name = "siRNA"
        verbose_name_plural = "siRNAs"

    _model_abbreviation = "siRNA"
    _model_upload_to = "collection/sirna/"

    name = models.CharField("name", max_length=255, blank=False)
    sequence = models.CharField("sequence - Sense", max_length=50, blank=False)
    sequence_antisense = models.CharField(
        "sequence - Antisense", max_length=50, blank=False
    )

    supplier = models.CharField("supplier", max_length=255, blank=False)
    supplier_part_no = models.CharField("supplier Part-No", max_length=255, blank=False)
    supplier_si_rna_id = models.CharField(
        "supplier siRNA ID", max_length=255, blank=False
    )
    species = models.ForeignKey(
        Species,
        verbose_name="organism",
        on_delete=models.PROTECT,
        null=True,
        blank=False,
    )
    target_genes = BetterArrayField(
        models.CharField(max_length=15), blank=False, null=True, default=list
    )
    locus_ids = BetterArrayField(
        models.CharField(max_length=15),
        verbose_name="locus IDs",
        blank=True,
        null=True,
        default=list,
    )
    description_comment = models.TextField(
        "description/comments",
        help_text="Include transfection conditions, etc. here",
        blank=True,
    )
    info_sheet = models.FileField(
        "info sheet",
        help_text="only .pdf files, max. 2 MB",
        upload_to=_model_upload_to,
        blank=True,
        null=True,
    )
    orders = models.ManyToManyField(
        Order, verbose_name="orders", related_name="%(class)s_order", blank=True
    )

    history_orders = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="order",
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
        # Remove all white spaces from sequence and set its length
        self.sequence = "".join(self.sequence.split())

        super().save(force_insert, force_update, using, update_fields)


################################################
#                   siRNA Doc                  #
################################################


class SiRnaDoc(DocFileMixin):
    class Meta:
        verbose_name = "siRNA document"

    _inline_foreignkey_fieldname = "si_rna"
    _mixin_props = {
        "destination_dir": "collection/sirnadoc/",
        "file_prefix": "sirnaDoc",
        "parent_field_name": "si_rna",
    }

    si_rna = models.ForeignKey(SiRna, on_delete=models.PROTECT)
