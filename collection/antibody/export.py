from import_export import resources

from .models import Antibody


class AntibodyExportResource(resources.ModelResource):
    """Defines a custom export resource class for Antibody"""

    class Meta:
        model = Antibody
        fields = (
            "id",
            "name",
            "species_isotype",
            "clone",
            "received_from",
            "catalogue_number",
            "l_ocation",
            "a_pplication",
            "description_comment",
            "info_sheet",
            "availability",
        )
        export_order = fields
