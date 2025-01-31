from django import forms

from .models import ScPombeStrain


class ScPombeStrainAdminForm(forms.ModelForm):
    def clean_name(self):
        """Check if name is unique before saving"""

        if not self.instance.pk:
            qs = ScPombeStrain.objects.filter(name=self.cleaned_data["name"])
            if qs:
                raise forms.ValidationError("Strain with this name already exists.")
            else:
                return self.cleaned_data["name"]
        else:
            return self.cleaned_data["name"]
