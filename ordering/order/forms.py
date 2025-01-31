from ast import literal_eval

from adminactions.mass_update import MassUpdateForm
from django import forms
from django.contrib.admin.widgets import AdminFileWidget
from django.forms import ValidationError
from django.utils.safestring import mark_safe

from ..models import GhsSymbol, Order


class GhsImageWidget(AdminFileWidget):
    """
    A custom widget that displays GHS pictograms
    """

    def render(self, name, value, attrs=None, renderer=None):
        output = []
        try:
            ghs_ids = literal_eval(value)
        except Exception:
            ghs_ids = []
        if ghs_ids:
            for ghs_pict in GhsSymbol.objects.filter(id__in=ghs_ids):
                output.append(
                    '<img style="max-height:100px; padding-right:10px;" src="{}" />'.format(
                        ghs_pict.pictogram.url
                    )
                )

        return mark_safe("".join(output))


class OrderAdminForm(forms.ModelForm):
    """
    Custom order form that contains a custom field to show GHS pictograms
    using GhsImageWidget
    """

    ghs_pict_img = forms.FileField(label="", widget=GhsImageWidget)

    class Meta:
        model = Order
        fields = "__all__"

    def clean(self):
        """
        If a GHS symbol is provided, check that a CAS number is also supplied.
        """

        ghs_symbols = self.cleaned_data.get("ghs_symbols")
        cas_number = self.cleaned_data.get("cas_number")
        hazard_statements = self.cleaned_data.get("hazard_statements")
        if ghs_symbols and not cas_number:
            raise ValidationError(
                {
                    "cas_number": "If you provide a GHS symbol, you must also enter a CAS number."
                }
            )
        if ghs_symbols and not hazard_statements:
            raise ValidationError(
                {
                    "hazard_statements": "If you provide a GHS symbol, you must also enter a hazard statement."
                }
            )

        return self.cleaned_data


class MassUpdateOrderForm(MassUpdateForm):
    _clean = None
    _validate = None

    class Meta:
        model = Order
        fields = [
            "supplier",
            "supplier_part_no",
            "internal_order_no",
            "part_description",
            "quantity",
            "price",
            "cost_unit",
            "location",
            "comment",
            "url",
            "cas_number",
            "ghs_symbols",
            "signal_words",
            "msds_form",
            "hazard_statements",
            "hazard_level_pregnancy",
        ]

    def clean__validate(self):
        return True

    def clean__clean(self):
        return False
