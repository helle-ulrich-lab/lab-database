from import_export import resources
from import_export.fields import Field

from .models import Plasmid


class PlasmidExportResource(resources.ModelResource):
    """Defines a custom export resource class for Plasmid"""

    additional_parent_vector_info = Field(
        attribute="old_parent_vector", column_name="additional_parent_vector_info"
    )

    class Meta:
        model = Plasmid
        fields = (
            "id",
            "name",
            "other_name",
            "parent_vector",
            "additional_parent_vector_info",
            "selection",
            "us_e",
            "construction_feature",
            "received_from",
            "note",
            "reference",
            "map",
            "created_date_time",
            "created_by__username",
        )
        export_order = fields
