from import_export import resources
from import_export.fields import Field

from .models import CellLine


class CellLineExportResource(resources.ModelResource):
    """Defines a custom export resource class for CellLine"""

    organism_name = Field()

    def dehydrate_organism_name(self, strain):
        return str(strain.organism)

    class Meta:
        model = CellLine
        fields = (
            "id",
            "name",
            "box_name",
            "alternative_name",
            "parental_line",
            "organism_name",
            "cell_type_tissue",
            "culture_type",
            "growth_condition",
            "freezing_medium",
            "received_from",
            "description_comment",
            "integrated_plasmids",
            "created_date_time",
            "created_by__username",
        )
        export_order = fields
