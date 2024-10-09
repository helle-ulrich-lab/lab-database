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


class Antibody(
    InfoSheetMaxSizeMixin,
    DownloadFileNameMixin,
    models.Model,
    SaveWithoutHistoricalRecord,
):

    _model_abbreviation = "ab"
    _model_upload_to = "collection/antibody/"

    name = models.CharField("name", max_length=255, blank=False)
    species_isotype = models.CharField("species/isotype", max_length=255, blank=False)
    clone = models.CharField("clone", max_length=255, blank=True)
    received_from = models.CharField("received from", max_length=255, blank=True)
    catalogue_number = models.CharField("catalogue number", max_length=255, blank=True)
    l_ocation = models.CharField("location", max_length=255, blank=True)
    a_pplication = models.CharField("application", max_length=255, blank=True)
    description_comment = models.TextField("description/comments", blank=True)
    info_sheet = models.FileField(
        "info sheet",
        help_text="only .pdf files, max. 2 MB",
        upload_to=_model_upload_to,
        blank=True,
        null=True,
    )
    availability = models.BooleanField("available?", default=True, null=False)

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
        verbose_name = "antibody"
        verbose_name_plural = "antibodies"


class AntibodyDoc(DocFileMixin):

    _inline_foreignkey_fieldname = "antibody"

    antibody = models.ForeignKey(Antibody, on_delete=models.PROTECT)

    _mixin_props = {
        "destination_dir": "collection/antibodydoc/",
        "file_prefix": "abDoc",
        "parent_field_name": "antibody",
    }

    class Meta:
        verbose_name = "antibody document"
