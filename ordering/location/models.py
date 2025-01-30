from django.db import models


class Location(models.Model):
    name = models.CharField("name", max_length=255, unique=True, blank=False)
    status = models.BooleanField(
        "deactivate?",
        help_text="Check it, if you want to HIDE this location from the 'Add new order' form ",
        default=False,
    )

    class Meta:
        ordering = [
            "name",
        ]

    def __str__(self):
        return self.name

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self.name = self.name.strip().lower()
        super().save(force_insert, force_update, using, update_fields)
