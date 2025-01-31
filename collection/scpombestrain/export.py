from import_export import resources
from import_export.fields import Field

from .models import ScPombeStrain


class ScPombeStrainExportResource(resources.ModelResource):
    """Defines a custom export resource class for ScPombeStrain"""

    additional_parental_strain_info = Field(
        attribute="parental_strain", column_name="additional_parental_strain_info"
    )
    episomal_plasmids_in_stock = Field()

    def dehydrate_episomal_plasmids_in_stock(self, strain):
        return (
            str(
                tuple(
                    strain.episomal_plasmids.filter(
                        scpombestrainepisomalplasmid__present_in_stocked_strain=True
                    ).values_list("id", flat=True)
                )
            )
            .replace(" ", "")
            .replace(",)", ")")[1:-1]
        )

    class Meta:
        model = ScPombeStrain
        fields = (
            "id",
            "box_number",
            "parent_1",
            "parent_2",
            "additional_parental_strain_info",
            "mating_type",
            "auxotrophic_marker",
            "name",
            "phenotype",
            "integrated_plasmids",
            "cassette_plasmids",
            "episomal_plasmids_in_stock",
            "received_from",
            "comment",
            "created_date_time",
            "created_by__username",
        )
        export_order = fields
