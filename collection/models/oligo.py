from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.postgres.fields import ArrayField
from django.db import models
from simple_history.models import HistoricalRecords

from approval.models import RecordToBeApproved
from collection.models.shared import InfoSheetMaxSizeMixin
from common.models import (
    DocFileMixin,
    DownloadFileNameMixin,
    SaveWithoutHistoricalRecord,
)
from formz.models import FormZBaseElement


class Oligo(
    InfoSheetMaxSizeMixin,
    DownloadFileNameMixin,
    models.Model,
    SaveWithoutHistoricalRecord,
):

    _model_abbreviation = "o"
    _model_upload_to = "collection/oligo/"

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
        help_text="only .pdf files, max. 2 MB",
        upload_to=_model_upload_to,
        blank=True,
        null=True,
    )

    created_date_time = models.DateTimeField("created", auto_now_add=True)
    created_approval_by_pi = models.BooleanField(
        "record creation approval", default=False
    )
    last_changed_date_time = models.DateTimeField("last changed", auto_now=True)
    last_changed_approval_by_pi = models.BooleanField(
        "record change approval", default=None, null=True
    )
    approval_by_pi_date_time = models.DateTimeField(null=True, default=None)
    approval = GenericRelation(RecordToBeApproved)
    created_by = models.ForeignKey(
        User, related_name="oligo_createdby_user", on_delete=models.PROTECT
    )
    history = HistoricalRecords()

    formz_elements = models.ManyToManyField(
        FormZBaseElement,
        verbose_name="elements",
        related_name="oligo_formz_element",
        blank=True,
    )
    history_formz_elements = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="formz elements",
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
        return "{} - {}".format(self.id, self.name)

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):

        # Remove all white spaces from sequence and set its length
        self.sequence = "".join(self.sequence.split())
        self.length = len(self.sequence)

        super(Oligo, self).save(force_insert, force_update, using, update_fields)


class OligoDoc(DocFileMixin):

    _inline_foreignkey_fieldname = "oligo"

    oligo = models.ForeignKey(Oligo, on_delete=models.PROTECT)

    _mixin_props = {
        "destination_dir": "collection/oligodoc/",
        "file_prefix": "oDoc",
        "parent_field_name": "oligo",
    }

    class Meta:
        verbose_name = "oligo document"
