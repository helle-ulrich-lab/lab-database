from django.db import models


class HazardStatement(models.Model):
    code = models.CharField("code", max_length=10, unique=True, blank=False)
    description = models.CharField("description", max_length=255, blank=False)
    is_cmr = models.BooleanField("is CMR?", default=False)

    class Meta:
        verbose_name = "hazard statement"

    def __str__(self):
        return f"{self.code}{' - CMR' if self.is_cmr else ''}"

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self.code = self.code.strip()
        self.description = self.description.strip()
        super().save(force_insert, force_update, using, update_fields)
