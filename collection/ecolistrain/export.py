from import_export import resources

from .models import EColiStrain


class EColiStrainExportResource(resources.ModelResource):
    """Defines a custom export resource class for EColiStrain"""

    class Meta:
        model = EColiStrain
        fields = (
            "id",
            "name",
            "resistance",
            "genotype",
            "supplier",
            "us_e",
            "purpose",
            "note",
            "created_date_time",
            "created_by__username",
        )
        export_order = fields
