import os

from django.conf import settings
from django.db import models
from django.forms import ValidationError
from django.utils import timezone
from django.utils.encoding import force_str

LAB_ABBREVIATION_FOR_FILES = getattr(settings, "LAB_ABBREVIATION_FOR_FILES", "")
MAX_UPLOAD_FILE_SIZE_MB = getattr(settings, "MAX_UPLOAD_FILE_SIZE_MB", 2)
ALLOWED_DOC_FILE_EXTS = getattr(settings, "ALLOWED_DOC_FILE_EXTS", ["pdf"])


class SaveWithoutHistoricalRecord:
    def save_without_historical_record(self, *args, **kwargs):
        """Allows inheritance of a method to save an object without
        saving a historical record as described in
        https://django-simple-history.readthedocs.io/en/2.7.2/querying_history.html?highlight=save_without_historical_record
        """

        self.skip_history_when_saving = True
        try:
            ret = self.save(*args, **kwargs)
        finally:
            del self.skip_history_when_saving
        return ret


class RenameFileField:
    def rename_file(self, field_name, new_file_name, upload_to):
        field = getattr(self, field_name)
        file_name = force_str(field)
        name, ext = os.path.splitext(file_name)
        ext = ext.lower()
        final_name = os.path.join(upload_to, f"{new_file_name}{ext}")

        # Essentially, rename file
        if file_name != final_name:
            field.storage.delete(final_name)
            field.storage.save(final_name, field)
            field.close()
            field.storage.delete(file_name)
            setattr(self, field_name, final_name)


class DocFileMixin(models.Model, RenameFileField):
    name = models.FileField(
        "file name", upload_to="temp/", max_length=150, blank=False, null=True
    )
    description = models.CharField("description", max_length=75, blank=False)
    comment = models.CharField("comment", max_length=150, blank=True)

    created_date_time = models.DateTimeField("created", auto_now_add=True)
    last_changed_date_time = models.DateTimeField("last changed", auto_now=True)

    class Meta:
        abstract = True

    # !!! Remember to set ForeignKey to parent model
    # !!! such Plasmid, Oligo, etc.

    # Override the following when inheriting DocFileMixin
    # in the final model
    _mixin_props = {
        "destination_dir": "collection/abc/",
        "file_prefix": "pabc",
        "parent_field_name": "abc",
    }

    @property
    def download_file_name(self):
        parent_field_name = self._mixin_props.get("parent_field_name")
        parent = getattr(self, parent_field_name)
        return (
            f"{parent._model_abbreviation}{LAB_ABBREVIATION_FOR_FILES}{parent}, "
            f"Doc# {self.id}, {self.description.title()}"
        )

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        # Rename a file of any given name to a standard name
        # after the corresponding entry has been created
        super().save(force_insert, force_update, using, update_fields)
        parent = getattr(self, self._mixin_props.get("parent_field_name"))
        new_file_name = (
            f"{self._mixin_props.get('file_prefix')}"
            f"{LAB_ABBREVIATION_FOR_FILES}{parent.id}_"
            f"{timezone.now().strftime('%Y%m%d_%H%M%S_%f')}_{self.id}"
        )
        self.rename_file(
            "name",
            new_file_name,
            self._mixin_props.get("destination_dir"),
        )
        super().save(False, True, using, update_fields)

    def __str__(self):
        return str(self.id)

    def clean(self):
        errors = []
        file_size_limit = MAX_UPLOAD_FILE_SIZE_MB * 1024 * 1024

        if self.name:
            # Check if file is bigger than X MB
            if self.name.size > file_size_limit:
                errors.append(
                    ValidationError(
                        f"File too large. Size cannot exceed {MAX_UPLOAD_FILE_SIZE_MB} MB."
                    )
                )

            # Check if file has extension
            try:
                file_ext = self.name.name.split(".")[-1].lower()
            except:
                errors.append(
                    ValidationError(
                        "Invalid file format. File does not have an extension"
                    )
                )
                file_ext = None
            if file_ext and file_ext not in ALLOWED_DOC_FILE_EXTS:
                errors.append(
                    ValidationError(
                        f'Invalid file format. Only {", ".join(ALLOWED_DOC_FILE_EXTS)} files are allowed'
                    )
                )

        if len(errors) > 0:
            raise ValidationError(errors)


class DownloadFileNameMixin:
    @property
    def download_file_name(self):
        return f"{self._model_abbreviation}{LAB_ABBREVIATION_FOR_FILES}{self}"
