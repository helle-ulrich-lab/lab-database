from import_export import resources
from import_export.fields import Field

from .models import Order


class BaseOrdeExportResource:
    ghs_symbols_field = Field(column_name="ghs_symbols")
    signal_words_field = Field(column_name="signal_words")
    hazard_statements_field = Field(column_name="hazard_statements")
    is_cmr_field = Field(column_name="is_cmr")

    def dehydrate_ghs_symbols_field(self, order):
        return ", ".join(order.ghs_symbols.all().values_list("code", flat=True))

    def dehydrate_signal_words_field(self, order):
        return ", ".join(order.signal_words.all().values_list("signal_word", flat=True))

    def dehydrate_hazard_statements_field(self, order):
        return ", ".join(order.hazard_statements.all().values_list("code", flat=True))

    def dehydrate_is_cmr_field(self, order):
        return "Yes" if order.hazard_statements.filter(is_cmr=True).exists() else ""


class OrderChemicalExportResource(BaseOrdeExportResource, resources.ModelResource):
    """
    Export resource for chemicals
    """

    class Meta:
        model = Order
        fields = (
            "id",
            "supplier",
            "supplier_part_no",
            "part_description",
            "quantity",
            "location__name",
            "cas_number",
            "ghs_symbols_field",
            "signal_words_field",
            "hazard_statements_field",
            "is_cmr_field",
            "hazard_level_pregnancy",
        )
        export_order = fields


class OrderExportResource(BaseOrdeExportResource, resources.ModelResource):
    """
    Export resource for orders
    """

    class Meta:
        model = Order
        fields = (
            "id",
            "internal_order_no",
            "supplier",
            "supplier_part_no",
            "part_description",
            "quantity",
            "price",
            "cost_unit__name",
            "status",
            "location__name",
            "comment",
            "url",
            "delivered_date",
            "cas_number",
            "ghs_symbols_field",
            "signal_words_field",
            "hazard_level_pregnancy",
            "created_date_time",
            "order_manager_created_date_time",
            "last_changed_date_time",
            "created_by__username",
        )
        export_order = fields
