from import_export import resources

from .models import Oligo


class OligoExportResource(resources.ModelResource):
    """Defines a custom export resource class for Oligo"""

    class Meta:
        model = Oligo
        fields = (
            "id",
            "name",
            "sequence",
            "us_e",
            "gene",
            "restriction_site",
            "description",
            "comment",
            "created_date_time",
            "created_by__username",
        )
        export_order = fields
