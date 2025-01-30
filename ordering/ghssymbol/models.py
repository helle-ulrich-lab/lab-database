from django.db import models
from django.forms import ValidationError
from common.models import RenameFileField


class GhsSymbol(models.Model, RenameFileField):
    _model_upload_to = "ordering/ghssymbol/"

    code = models.CharField("code", max_length=10, unique=True, blank=False)
    pictogram = models.ImageField(
        "pictogram",
        upload_to="temp/",
        help_text="only .png images, max. 2 MB",
        blank=False,
    )
    description = models.CharField("description", max_length=255, blank=False)

    class Meta:
        verbose_name = "GHS symbol"

    def __str__(self):
        return f"{self.code} - {self.description}"

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self.code = self.code.strip().upper()
        self.description = self.description.strip()

        # Rename a file of any given name to ghs_{id}_{code}.xxx,
        # after the corresponding entry has been created
        super().save(force_insert, force_update, using, update_fields)
        self.rename_file(
            "pictogram", f"ghs_{self.id}_{self.code}", self._model_upload_to
        )
        super().save(False, True, using, update_fields)

    def clean(self):
        errors = []
        file_size_limit = 2 * 1024 * 1024

        if self.pictogram:
            # Check if file is bigger than 2 MB
            if self.pictogram.size > file_size_limit:
                errors.append(
                    ValidationError("File too large. Size cannot exceed 2 MB.")
                )

            # Check if file has extension
            try:
                img_ext = self.pictogram.name.split(".")[-1].lower()
            except Exception:
                img_ext = None
            if img_ext is None or img_ext != "png":
                errors.append(
                    ValidationError(
                        "Invalid file format. Please select a valid .png file"
                    )
                )

        if len(errors) > 0:
            raise ValidationError(errors)
