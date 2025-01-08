from django.db import models

from collection.models.shared import (
    HistoryDocFieldMixin,
    HistoryFieldMixin,
    InfoSheetMaxSizeMixin,
    OwnershipFieldsMixin,
)
from common.models import (
    DocFileMixin,
    DownloadFileNameMixin,
    SaveWithoutHistoricalRecord,
)

################################################
#                   Antibody                   #
################################################


class Antibody(
    SaveWithoutHistoricalRecord,
    DownloadFileNameMixin,
    InfoSheetMaxSizeMixin,
    HistoryDocFieldMixin,
    HistoryFieldMixin,
    OwnershipFieldsMixin,
    models.Model,
):
    class Meta:
        verbose_name = "antibody"
        verbose_name_plural = "antibodies"

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

    def __str__(self):
        return f"{self.id} - {self.name}"


################################################
#                 Antibody Doc                 #
################################################


class AntibodyDoc(DocFileMixin):
    class Meta:
        verbose_name = "antibody document"

    _inline_foreignkey_fieldname = "antibody"
    _mixin_props = {
        "destination_dir": "collection/antibodydoc/",
        "file_prefix": "abDoc",
        "parent_field_name": "antibody",
    }

    antibody = models.ForeignKey(Antibody, on_delete=models.PROTECT)
