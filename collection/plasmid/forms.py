from django import forms

from .models import Plasmid


class PlasmidAdminForm(forms.ModelForm):
    class Meta:
        model = Plasmid
        fields = "__all__"

    def clean_name(self):
        """Check if name is unique before saving"""

        if not self.instance.pk:
            if self._meta.model.objects.filter(name=self.cleaned_data["name"]).exists():
                raise forms.ValidationError("Plasmid with this name already exists.")
            else:
                return self.cleaned_data["name"]
        else:
            if (
                self._meta.model.objects.filter(name=self.cleaned_data["name"])
                .exclude(id=self.instance.pk)
                .exists()
            ):
                raise forms.ValidationError("Plasmid with this name already exists.")
            else:
                return self.cleaned_data["name"]

    def clean(self):
        """Check if both the .dna and .gbk map is changed at the same time, which
        is not allowed"""

        map_dna = self.cleaned_data.get("map", None)
        map_gbk = self.cleaned_data.get("map_gbk", None)

        if not self.instance.pk:
            if map_dna and map_gbk:
                self.add_error(
                    None,
                    "You cannot add both a .dna and a .gbk map at the same time. "
                    "Please choose only one",
                )

        else:
            saved_obj = self._meta.model.objects.get(id=self.instance.pk)
            saved_dna_map = saved_obj.map.name if saved_obj.map.name else None
            saved_gbk_map = saved_obj.map_gbk.name if saved_obj.map_gbk.name else None

            if map_dna != saved_dna_map and map_gbk != saved_gbk_map:
                self.add_error(
                    None,
                    "You cannot change both a .dna and a .gbk map at the same time. "
                    "Please choose only one",
                )

        return self.cleaned_data
