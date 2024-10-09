from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.db import models
from simple_history.models import HistoricalRecords

from collection.models.shared import InfoSheetMaxSizeMixin
from common.models import (
    DocFileMixin,
    DownloadFileNameMixin,
    SaveWithoutHistoricalRecord,
)


class Inhibitor(
    InfoSheetMaxSizeMixin,
    DownloadFileNameMixin,
    models.Model,
    SaveWithoutHistoricalRecord,
):

    _model_abbreviation = "ib"
    _model_upload_to = "collection/inhibitor/"

    name = models.CharField("name", max_length=255, blank=False)
    other_names = models.CharField("other names", max_length=255, blank=False)
    target = models.CharField("target", max_length=255, blank=True)
    received_from = models.CharField("received from", max_length=255, blank=True)
    catalogue_number = models.CharField("catalogue number", max_length=255, blank=True)
    l_ocation = models.CharField("location", max_length=255, blank=True)
    ic50 = models.CharField("IC50", max_length=255, blank=True)
    amount = models.CharField("amount", max_length=255, blank=True)
    stock_solution = models.CharField("stock solution", max_length=255, blank=True)
    description_comment = models.TextField("description/comments", blank=True)
    info_sheet = models.FileField(
        "info sheet",
        help_text="only .pdf files, max. 2 MB",
        upload_to=_model_upload_to,
        blank=True,
        null=True,
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

    class Meta:
        verbose_name = "inhibitor"
        verbose_name_plural = "inhibitors"

    def __str__(self):
        return str(self.id)


class InhibitorDoc(DocFileMixin):
    inhibitor = models.ForeignKey(Inhibitor, on_delete=models.PROTECT)

    _mixin_props = {
        "destination_dir": "collection/inhibitordoc/",
        "file_prefix": "ibDoc",
        "parent_field_name": "inhibitor",
    }

    class Meta:
        verbose_name = "inhibitor document"
