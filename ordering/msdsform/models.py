import os

from django.db import models
from django.forms import ValidationError


class MsdsForm(models.Model):
    _model_upload_to = "ordering/msdsform/"

    label = models.CharField("label", max_length=255, blank=True)
    name = models.FileField(
        "file name",
        help_text="max. 2 MB",
        upload_to=_model_upload_to,
        unique=True,
        blank=False,
    )

    created_date_time = models.DateTimeField("created", auto_now_add=True, null=True)
    last_changed_date_time = models.DateTimeField(
        "last changed", auto_now=True, null=True
    )

    class Meta:
        verbose_name = "MSDS form"

    def __str__(self):
        return self.file_name_description

    @property
    def file_name_description(self):
        short_name = os.path.basename(self.label).split(".")
        short_name = ".".join(short_name[:-1]).replace("_", " ")
        return short_name

    @property
    def download_file_name(self):
        return self.label

    def clean(self):
        errors = []
        file_size_limit = 2 * 1024 * 1024

        if self.name:
            # Check if file is bigger than 2 MB
            if self.name.size > file_size_limit:
                errors.append(
                    ValidationError("File too large. Size cannot exceed 2 MB.")
                )

            # Check if file has extension
            try:
                self.name.name.split(".")[-1].lower()
            except Exception:
                errors.append(
                    ValidationError(
                        "Invalid file format. File does not have an extension"
                    )
                )

            if any(c.isspace() for c in self.name.name):
                errors.append(ValidationError("File name cannot contain white spaces."))

        if len(errors) > 0:
            raise ValidationError(errors)
