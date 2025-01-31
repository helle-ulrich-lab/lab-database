from django import forms
from django.conf import settings

from ..shared.admin import (
    FormTwoMapChangeCheck,
    OptionalChoiceField,
)
from .models import WormStrain

WORM_ALLELE_LAB_IDS = getattr(settings, "WORM_ALLELE_LAB_IDS", [])


class WormStrainAdminForm(forms.ModelForm):
    class Meta:
        model = WormStrain
        fields = "__all__"

    def clean_name(self):
        """Check if name is unique before saving"""

        if not self.instance.pk:
            qs = self._meta.model.objects.filter(name=self.cleaned_data["name"])
            if qs.exists():
                raise forms.ValidationError("Strain with this name already exists.")
            else:
                return self.cleaned_data["name"]
        else:
            return self.cleaned_data["name"]


class WormStrainAlleleAdminForm(FormTwoMapChangeCheck, forms.ModelForm):
    if WORM_ALLELE_LAB_IDS:
        lab_identifier = OptionalChoiceField(
            choices=WORM_ALLELE_LAB_IDS,
        )
