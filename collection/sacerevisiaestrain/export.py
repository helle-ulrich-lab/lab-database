from import_export import resources
from import_export.fields import Field

from .models import SaCerevisiaeStrain


class SaCerevisiaeStrainExportResource(resources.ModelResource):
    """Defines a custom export resource class for SaCerevisiaeStrain"""

    episomal_plasmids_in_stock = Field()
    other_plasmids = Field(attribute="plasmids", column_name="other_plasmids_info")
    additional_parental_strain_info = Field(
        attribute="parental_strain", column_name="additional_parental_strain_info"
    )

    def dehydrate_episomal_plasmids_in_stock(self, strain):
        return (
            str(
                tuple(
                    strain.episomal_plasmids.filter(
                        sacerevisiaestrainepisomalplasmid__present_in_stocked_strain=True
                    ).values_list("id", flat=True)
                )
            )
            .replace(" ", "")
            .replace(",)", ")")[1:-1]
        )

    class Meta:
        model = SaCerevisiaeStrain
        fields = (
            "id",
            "name",
            "relevant_genotype",
            "mating_type",
            "chromosomal_genotype",
            "parent_1",
            "parent_2",
            "additional_parental_strain_info",
            "construction",
            "modification",
            "integrated_plasmids",
            "cassette_plasmids",
            "episomal_plasmids_in_stock",
            "other_plasmids",
            "selection",
            "phenotype",
            "background",
            "received_from",
            "us_e",
            "note",
            "reference",
            "created_date_time",
            "created_by__username",
        )
        export_order = fields
