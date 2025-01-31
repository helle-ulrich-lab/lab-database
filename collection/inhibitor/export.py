from import_export import resources

from .models import Inhibitor


class InhibitorExportResource(resources.ModelResource):
    """Custom export resource class for Inhibitor"""

    class Meta:
        model = Inhibitor
        fields = (
            "id",
            "name",
            "other_names",
            "target",
            "received_from",
            "catalogue_number",
            "l_ocation",
            "ic50",
            "amount",
            "stock_solution",
            "description_comment",
            "info_sheet",
        )
        export_order = fields
