from django.db import models

from common.models import DocFileMixin, HistoryFieldMixin, SaveWithoutHistoricalRecord
from formz.models import FormZBaseElement, FormZProject

from ..shared.models import (
    ApprovalFieldsMixin,
    CommonCollectionModelPropertiesMixin,
    FormZFieldsMixin,
    HistoryDocFieldMixin,
    OwnershipFieldsMixin,
)


class EColiStrainDoc(DocFileMixin):
    class Meta:
        verbose_name = "e. coli strain document"

    _inline_foreignkey_fieldname = "ecoli_strain"
    _mixin_props = {
        "destination_dir": "collection/ecolistraindoc/",
        "file_prefix": "ecDoc",
        "parent_field_name": "ecoli_strain",
    }

    ecoli_strain = models.ForeignKey("EColiStrain", on_delete=models.PROTECT)


class EColiStrain(
    SaveWithoutHistoricalRecord,
    CommonCollectionModelPropertiesMixin,
    HistoryDocFieldMixin,
    FormZFieldsMixin,
    HistoryFieldMixin,
    ApprovalFieldsMixin,
    OwnershipFieldsMixin,
    models.Model,
):
    class Meta:
        verbose_name = "strain - E. coli"
        verbose_name_plural = "strains - E. coli"

    _model_abbreviation = "ec"
    _history_array_fields = {
        "history_formz_projects": FormZProject,
        "history_formz_elements": FormZBaseElement,
        "history_documents": EColiStrainDoc,
    }
    _history_view_ignore_fields = (
        ApprovalFieldsMixin._history_view_ignore_fields
        + OwnershipFieldsMixin._history_view_ignore_fields
    )

    name = models.CharField("name", max_length=255, blank=False)
    resistance = models.CharField("resistance", max_length=255, blank=True)
    genotype = models.TextField("genotype", blank=True)
    background = models.CharField(
        "background",
        max_length=255,
        choices=(("B", "B"), ("C", "C"), ("K12", "K12"), ("W", "W")),
        blank=True,
    )
    supplier = models.CharField("supplier", max_length=255)
    us_e = models.CharField(
        "use",
        max_length=255,
        choices=(
            ("Cloning", "Cloning"),
            ("Expression", "Expression"),
            ("Other", "Other"),
        ),
    )
    purpose = models.TextField("purpose", blank=True)
    note = models.TextField("note", max_length=255, blank=True)

    formz_gentech_methods = None
    history_formz_gentech_methods = None

    def __str__(self):
        return f"{self.id} - {self.name}"
