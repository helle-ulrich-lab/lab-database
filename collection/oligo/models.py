from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models

from common.models import (
    DocFileMixin,
    DownloadFileNameMixin,
    HistoryFieldMixin,
    SaveWithoutHistoricalRecord,
)
from formz.models import SequenceFeature

from ..shared.models import (
    ApprovalFieldsMixin,
    HistoryDocFieldMixin,
    InfoSheetMaxSizeMixin,
    OwnershipFieldsMixin,
)

FILE_SIZE_LIMIT_MB = getattr(settings, "FILE_SIZE_LIMIT_MB", 2)


class OligoDoc(DocFileMixin):
    class Meta:
        verbose_name = "oligo document"

    _inline_foreignkey_fieldname = "oligo"
    _mixin_props = {
        "destination_dir": "collection/oligodoc/",
        "file_prefix": "oDoc",
        "parent_field_name": "oligo",
    }

    oligo = models.ForeignKey("Oligo", on_delete=models.PROTECT)


class Oligo(
    SaveWithoutHistoricalRecord,
    DownloadFileNameMixin,
    InfoSheetMaxSizeMixin,
    HistoryDocFieldMixin,
    HistoryFieldMixin,
    ApprovalFieldsMixin,
    OwnershipFieldsMixin,
    models.Model,
):
    class Meta:
        verbose_name = "oligo"
        verbose_name_plural = "oligos"

    _model_abbreviation = "o"
    _model_upload_to = "collection/oligo/"
    _history_array_fields = {
        "history_sequence_features": SequenceFeature,
        "history_documents": OligoDoc,
    }
    _history_view_ignore_fields = (
        ApprovalFieldsMixin._history_view_ignore_fields
        + OwnershipFieldsMixin._history_view_ignore_fields
    )

    name = models.CharField("name", max_length=255, unique=True, blank=False)
    sequence = models.CharField(
        "sequence",
        max_length=255,
        unique=True,
        db_collation="case_insensitive",
        blank=False,
    )
    length = models.SmallIntegerField("length", null=True)
    us_e = models.CharField("use", max_length=255, blank=True)
    gene = models.CharField("gene", max_length=255, blank=True)
    restriction_site = models.CharField("restriction sites", max_length=255, blank=True)
    description = models.TextField("description", blank=True)
    comment = models.CharField("comments", max_length=255, blank=True)
    info_sheet = models.FileField(
        "info sheet",
        help_text=f"only .pdf files, max. {FILE_SIZE_LIMIT_MB} MB",
        upload_to=_model_upload_to,
        blank=True,
        null=True,
    )

    sequence_features = models.ManyToManyField(
        SequenceFeature,
        verbose_name="elements",
        related_name="%(class)s_sequence_features",
        blank=True,
    )
    history_sequence_features = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="formz elements",
        blank=True,
        null=True,
        default=list,
    )

    approval_user = None

    def __str__(self):
        return f"{self.id} - {self.name}"

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        # Remove all white spaces from sequence and set its length
        self.sequence = "".join(self.sequence.split())
        self.length = len(self.sequence)

        super().save(force_insert, force_update, using, update_fields)
