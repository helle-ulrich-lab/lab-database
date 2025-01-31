from import_export import resources
from import_export.fields import Field

from .models import (
    WormStrain,
    WormStrainAllele,
)


class WormStrainExportResource(resources.ModelResource):
    """Defines a custom export resource class for WormStrain"""

    primers_for_genotyping = Field()

    def dehydrate_primers_for_genotyping(self, strain):
        return str(strain.history_genotyping_oligos)[1:-1]

    class Meta:
        model = WormStrain
        fields = (
            "id",
            "name",
            "chromosomal_genotype",
            "parent_1",
            "parent_2",
            "construction",
            "outcrossed",
            "growth_conditions",
            "organism",
            "integrated_dna_plasmids",
            "integrated_dna_oligos",
            "selection",
            "phenotype",
            "received_from",
            "us_e",
            "note",
            "reference",
            "at_cgc",
            "location_freezer1",
            "location_freezer2",
            "location_backup",
            "primers_for_genotyping",
            "created_date_time",
            "created_by__username",
        )
        export_order = fields


class WormStrainAlleleExportResource(resources.ModelResource):
    """Defines a custom export resource class for WormStrainAllele"""

    made_by_method = Field()
    type = Field()

    def dehydrate_made_by_method(self, strain):
        return strain.made_by_method.english_name

    def dehydrate_type(self, strain):
        return strain.get_typ_e_display()

    class Meta:
        model = WormStrainAllele
        fields = (
            "id",
            "lab_identifier",
            "type",
            "transgene",
            "transgene_position",
            "transgene_plasmids",
            "mutation",
            "mutation_type",
            "mutation_position",
            "reference_strain",
            "made_by_method",
            "made_by_person",
            "made_with_plasmids",
            "notes",
            "created_date_time",
            "created_by__username",
        )
        export_order = fields
