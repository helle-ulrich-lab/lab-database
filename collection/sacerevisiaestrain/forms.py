from django import forms

from .models import SaCerevisiaeStrain


class SaCerevisiaeStrainAdminForm(forms.ModelForm):
    class Meta:
        model = SaCerevisiaeStrain
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
