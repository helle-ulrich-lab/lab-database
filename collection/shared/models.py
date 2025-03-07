import base64
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.forms import ValidationError

from approval.models import Approval
from formz.models import FormZBaseElement, FormZProject, GenTechMethod

FILE_SIZE_LIMIT_MB = getattr(settings, "FILE_SIZE_LIMIT_MB", 2)
OVE_URL = getattr(settings, "OVE_URL", "")
LAB_ABBREVIATION_FOR_FILES = getattr(settings, "LAB_ABBREVIATION_FOR_FILES", "")
MEDIA_URL = settings.MEDIA_URL


class ApprovalFieldsMixin(models.Model):
    """Common approval fields"""

    class Meta:
        abstract = True

    _history_view_ignore_fields = [
        "created_approval_by_pi",
        "last_changed_approval_by_pi",
        "approval_by_pi_date_time",
        "approval",
        "approval_user",
    ]

    created_approval_by_pi = models.BooleanField(
        "record creation approval", default=False
    )
    last_changed_approval_by_pi = models.BooleanField(
        "record change approval", default=None, null=True
    )
    approval_by_pi_date_time = models.DateTimeField(null=True, default=None)
    approval = GenericRelation(Approval)
    approval_user = models.ForeignKey(
        User,
        related_name="%(class)s_approval_user",
        on_delete=models.PROTECT,
        null=True,
    )


class OwnershipFieldsMixin(models.Model):
    """Common ownership fields"""

    class Meta:
        abstract = True

    _history_view_ignore_fields = [
        "created_date_time",
        "last_changed_date_time",
    ]

    created_date_time = models.DateTimeField("created", auto_now_add=True)
    last_changed_date_time = models.DateTimeField("last changed", auto_now=True)
    created_by = models.ForeignKey(
        User, related_name="%(class)s_createdby_user", on_delete=models.PROTECT
    )


class HistoryDocFieldMixin(models.Model):
    """Common history doc field"""

    class Meta:
        abstract = True

    history_documents = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="documents",
        blank=True,
        null=True,
        default=list,
    )


class HistoryPlasmidsFieldsMixin(models.Model):
    """Common history field to keep information for different
    kinds of plasmids"""

    class Meta:
        abstract = True

    history_integrated_plasmids = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="integrated plasmid",
        blank=True,
        null=True,
        default=list,
    )
    history_cassette_plasmids = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="cassette plasmids",
        blank=True,
        null=True,
        default=list,
    )
    history_episomal_plasmids = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="episomal plasmids",
        blank=True,
        null=True,
        default=list,
    )
    history_all_plasmids_in_stocked_strain = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="all plasmids in stocked strain",
        blank=True,
        null=True,
        default=list,
    )


class FormZFieldsMixin(models.Model):
    """Common FormZ fields"""

    class Meta:
        abstract = True

    formz_projects = models.ManyToManyField(
        FormZProject,
        verbose_name="projects",
        related_name="%(class)s_formz_projects",
        blank=False,
    )
    formz_risk_group = models.PositiveSmallIntegerField(
        "risk group", choices=((1, 1), (2, 2)), blank=False, null=True
    )
    formz_gentech_methods = models.ManyToManyField(
        GenTechMethod,
        verbose_name="genTech methods",
        help_text="The genetic method(s) used to create this record",
        related_name="%(class)s_gentech_methods",
        blank=True,
    )
    formz_elements = models.ManyToManyField(
        FormZBaseElement,
        verbose_name="elements",
        help_text="Use only when an element is not present in the chosen plasmid(s), if any. "
        "Searching against the aliases of an element is case-sensitive. "
        '<a href="/formz/formzbaseelement/" target="_blank">View all/Change</a>',
        related_name="%(class)s_formz_elements",
        blank=True,
    )
    destroyed_date = models.DateField("destroyed", blank=True, null=True)

    history_formz_projects = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="formZ projects",
        blank=True,
        null=True,
        default=list,
    )
    history_formz_gentech_methods = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="genTech methods",
        blank=True,
        null=True,
        default=list,
    )
    history_formz_elements = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="formz elements",
        blank=True,
        null=True,
        default=list,
    )


class InfoSheetMaxSizeMixin:
    """Clean method for models that have an info sheet"""

    def clean(self):
        errors = {}
        file_size_limit = FILE_SIZE_LIMIT_MB * 1024 * 1024

        if self.info_sheet:
            # Check if file is bigger than FILE_SIZE_LIMIT_MB
            if self.info_sheet.size > file_size_limit:
                errors["info_sheet"] = errors.get("info_sheet", []) + [
                    f"File too large. Size cannot exceed {FILE_SIZE_LIMIT_MB} MB."
                ]

            # Check if file's extension is '.pdf'
            try:
                info_sheet_ext = self.info_sheet.name.split(".")[-1].lower()
            except Exception:
                info_sheet_ext = None
            if info_sheet_ext is None or info_sheet_ext != "pdf":
                errors["info_sheet"] = errors.get("info_sheet", []) + [
                    "Invalid file format. Please select a valid .pdf file"
                ]

        if errors:
            raise ValidationError(errors)


class MapFileChecPropertieskMixin:
    """Clean method and common properties for models that have a map sheet"""

    def clean(self):
        errors = {}

        file_size_limit = FILE_SIZE_LIMIT_MB * 1024 * 1024

        # Check .dna map
        if self.map:
            # Check if file is bigger than FILE_SIZE_LIMIT_MB
            if self.map.size > file_size_limit:
                errors["map"] = errors.get("map", []) + [
                    f"The map is too large. Size cannot exceed {FILE_SIZE_LIMIT_MB} MB."
                ]

            # Check if file's extension is '.dna'
            try:
                map_ext = self.map.name.split(".")[-1].lower()
            except Exception:
                map_ext = None
            if map_ext is None or map_ext != "dna":
                errors["map"] = errors.get("map", []) + [
                    "Invalid file format. Please select a valid SnapGene .dna file"
                ]
            else:
                # Check if .dna file is a real SnapGene file

                dna_map_handle = self.map.open("rb")

                first_byte = dna_map_handle.read(1)
                dna_map_handle.read(4)
                title = dna_map_handle.read(8).decode("ascii")
                if first_byte != b"\t" and title != "SnapGene":
                    errors["map"] = errors.get("map", []) + [
                        "Invalid file format. Please select a valid SnapGene .dna file"
                    ]

        if self.map_gbk:
            # Check if file is bigger than FILE_SIZE_LIMIT_MB
            if self.map_gbk.size > file_size_limit:
                errors["map_gbk"] = errors.get("map_gbk", []) + [
                    f"The map is too large. Size cannot exceed {FILE_SIZE_LIMIT_MB} MB."
                ]

            # Check if file's extension is '.gbk'
            try:
                map_ext = self.map_gbk.name.split(".")[-1].lower()
            except Exception:
                map_ext = None
            if map_ext is None or map_ext not in ["gbk", "gb"]:
                errors["map_gbk"] = errors.get("map_gbk", []) + [
                    "Invalid file format. Please select a valid GenBank (.gbk or .gb) file"
                ]

        if errors:
            raise ValidationError(errors)

    @property
    def png_map_as_base64(self):
        """Returns html image element for map"""

        png_data = base64.b64encode(open(self.map_png.path, "rb").read()).decode(
            "ascii"
        )
        return str(png_data)

    @property
    def utf8_encoded_gbk(self):
        """Returns a decoded gbk plasmid map"""

        return self.map_gbk.read().decode()

    @property
    def map_ove_url(self):
        """Returns the url to view the a SnapGene file in OVE"""

        params = {
            "file_name": self.map.url,
            "title": f"{self._model_abbreviation}{LAB_ABBREVIATION_FOR_FILES}{self.__str__()}",
            "file_format": "dna",
        }

        return f"{OVE_URL}?{urlencode(params)}"

    @property
    def map_ove_url_gbk(self):
        """Returns the url to view the a gbk file in OVE"""

        params = {
            "file_name": self.map_gbk.url,
            "title": f"{self._model_abbreviation}{LAB_ABBREVIATION_FOR_FILES}{self.__str__()}",
            "file_format": "gbk",
        }

        return f"{OVE_URL}?{urlencode(params)}"

    @property
    def find_oligos_map_gbk_ove_url(self):
        """Returns the url to import all oligos into the plasmid map
        and view it in OVE"""

        params = {
            "file_name": f"/{self._meta.app_label}/{self._meta.model_name}/{self.pk}/find_oligos/",
            "title": f"{self._model_abbreviation}{LAB_ABBREVIATION_FOR_FILES}{self.__str__()} (imported oligos)",
            "file_format": "gbk",
            "show_oligos": "true",
        }

        return f"{OVE_URL}?{urlencode(params)}"


class CommonCollectionModelPropertiesMixin:
    @property
    def all_instock_plasmids(self):
        """Returns all plasmids present in the stocked organism"""

        return []

    @property
    def all_transient_episomal_plasmids(self):
        """Returns all transiently transformed episomal plasmids"""

        return []

    @property
    def all_plasmids_with_maps(self):
        """Returns all plasmids with a map"""
        return []

    @property
    def all_uncommon_formz_elements(self):
        """Returns all uncommon features in stocked organism"""

        elements = self.formz_elements.filter(common_feature=False).order_by("name")
        return elements

    @property
    def all_common_formz_elements(self):
        """Returns all common features in stocked organism"""

        elements = self.formz_elements.filter(common_feature=True).order_by("name")
        return elements
