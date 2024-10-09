from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django_better_admin_arrayfield.models.fields import ArrayField as BetterArrayField
from simple_history.models import HistoricalRecords

from collection.models.shared import InfoSheetMaxSizeMixin
from common.models import (
    DocFileMixin,
    DownloadFileNameMixin,
    SaveWithoutHistoricalRecord,
)
from formz.models import Species
from ordering.models import Order


class SiRna(
    InfoSheetMaxSizeMixin,
    DownloadFileNameMixin,
    models.Model,
    SaveWithoutHistoricalRecord,
):

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
        Order, verbose_name="orders", related_name="si_rna_order", blank=True
    )

    # Fields to keep a record of M2M field values (only IDs!) in the main strain record
    history_orders = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="order",
        blank=True,
        null=True,
        default=list,
    )

    created_date_time = models.DateTimeField("created", auto_now_add=True)
    last_changed_date_time = models.DateTimeField("last changed", auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    history = HistoricalRecords()

    history_documents = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="documents",
        blank=True,
        null=True,
        default=list,
    )

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):

        # Remove all white spaces from sequence and set its length
        self.sequence = "".join(self.sequence.split())

        super().save(force_insert, force_update, using, update_fields)

    class Meta:
        verbose_name = "siRNA"
        verbose_name_plural = "siRNAs"

    def __str__(self):
        return f"{self.id} - {self.name}"


class SiRnaDoc(DocFileMixin):

    _inline_foreignkey_fieldname = "si_rna"

    si_rna = models.ForeignKey(SiRna, on_delete=models.PROTECT)

    _mixin_props = {
        "destination_dir": "collection/sirnadoc/",
        "file_prefix": "sirnaDoc",
        "parent_field_name": "si_rna",
    }

    class Meta:
        verbose_name = "siRNA document"
