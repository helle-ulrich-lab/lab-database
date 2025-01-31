from django import forms

from .models import Oligo


class OligoAdminForm(forms.ModelForm):
    class Meta:
        model = Oligo
        fields = "__all__"

    def clean_sequence(self):
        """Check if sequence is unique before saving"""

        sequence = self.cleaned_data["sequence"]
        qs = self._meta.model.objects.filter(sequence=sequence)

        if not self.instance.pk:
            if qs.exists():
                raise forms.ValidationError("Oligo with this Sequence already exists.")
        else:
            if qs.exclude(id=self.instance.pk).exists():
                raise forms.ValidationError("Oligo with this Sequence already exists.")

        return sequence

    def clean_name(self):
        """Check if name is unique before saving"""

        name = self.cleaned_data["name"]
        qs = self._meta.model.objects.filter(name=name)

        if not self.instance.pk:
            if qs.exists():
                raise forms.ValidationError("Oligo with this Name already exists.")
        else:
            if qs.exclude(id=self.instance.pk).exists():
                raise forms.ValidationError("Oligo with this Name already exists.")

        return name
