from django.db import models


class CostUnit(models.Model):
    name = models.CharField("Name", max_length=255, unique=True, blank=False)
    description = models.CharField(
        "Description", max_length=255, unique=True, blank=False
    )
    status = models.BooleanField(
        "deactivate?",
        help_text="Check it, if you want to HIDE this cost unit from the 'Add new order' form",
        default=False,
    )

    class Meta:
        verbose_name = "cost unit"
        ordering = [
            "name",
        ]

    def __str__(self):
        return f"{self.name} - {self.description}"

    def save(self, force_insert=False, force_update=False):
        self.name = self.name.strip().lower()
        super().save(force_insert, force_update)
