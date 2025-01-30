from django.db import models


class SignalWord(models.Model):
    signal_word = models.CharField(
        "signal word", max_length=255, unique=True, blank=False
    )

    class Meta:
        verbose_name = "signal word"

    def __str__(self):
        return self.signal_word

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self.signal_word = self.signal_word.strip()
        super().save(force_insert, force_update, using, update_fields)
