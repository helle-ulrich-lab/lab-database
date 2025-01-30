from django import forms

from .models import MsdsForm


class MsdsFormForm(forms.ModelForm):
    class Meta:
        model = MsdsForm
        fields = "__all__"

    def clean(self):
        # Check if the name of a MSDS form is unique before saving
        name = getattr(self.cleaned_data["name"], "name", "")
        if name:
            qs = self.model.objects.filter(label=name)
            if qs.exists():
                self.add_error("name", "A form with this file name already exists.")
        return self.cleaned_data
