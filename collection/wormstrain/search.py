from django.contrib.auth.models import User
from django.db.models import Q
from djangoql.schema import DjangoQLSchema, IntField, StrField

from common.search import (
    SearchFieldUserLastnameWithOptions,
    SearchFieldUserUsernameWithOptions,
)

from ..shared.admin import (
    FieldCreated,
    FieldFormZBaseElement,
    FieldFormZProject,
    FieldLastChanged,
    FieldParent1,
    FieldParent2,
    FieldUse,
)
from .models import WormStrain, WormStrainAllele


class WormStrainSearchFieldUserUsername(SearchFieldUserUsernameWithOptions):
    id_list = WormStrain.objects.all().values_list("created_by", flat=True).distinct()


class WormStrainSearchFieldUserLastname(SearchFieldUserLastnameWithOptions):
    id_list = WormStrain.objects.all().values_list("created_by", flat=True).distinct()


class WormStrainSearchFieldAlleleName(StrField):
    model = WormStrainAllele
    name = "allele_name"
    suggest_options = True

    def get_options(self, search):
        if len(search) < 3:
            return ["Type 3 or more characters to see suggestions"]

        qs = self.model.objects.filter(
            Q(transgene__icontains=search) | Q(mutation__icontains=search)
        )
        return [a.name for a in qs]

    def get_lookup(self, path, operator, value):
        op, invert = self.get_operator(operator)
        value = self.get_lookup_value(value)

        q = Q(**{f"alleles__transgene{op}": value}) | Q(
            **{f"alleles__mutation{op}": value}
        )

        return ~q if invert else q


class WormStrainSearchFieldAlleleId(IntField):
    model = WormStrainAllele
    name = "allele_id"
    suggest_options = False

    def get_lookup_name(self):
        return "alleles__id"


class WormStrainQLSchema(DjangoQLSchema):
    """Customize search functionality"""

    include = (WormStrain, User)  # Include only the relevant models to be searched

    def get_fields(self, model):
        """Define fields that can be searched"""

        if model == WormStrain:
            return [
                "id",
                "name",
                "chromosomal_genotype",
                FieldParent1(),
                FieldParent2(),
                "construction",
                "outcrossed",
                "growth_conditions",
                "organism",
                "selection",
                "phenotype",
                "received_from",
                FieldUse(),
                "note",
                "reference",
                "at_cgc",
                "location_freezer1",
                "location_freezer2",
                "location_backup",
                WormStrainSearchFieldAlleleId(),
                WormStrainSearchFieldAlleleName(),
                "created_by",
                FieldCreated(),
                FieldLastChanged(),
                FieldFormZProject(),
            ]
        elif model == User:
            return [
                WormStrainSearchFieldUserUsername(),
                WormStrainSearchFieldUserLastname(),
            ]
        return super().get_fields(model)


class WormStrainAlleleSearchFieldUserUsername(SearchFieldUserUsernameWithOptions):
    id_list = (
        WormStrainAllele.objects.all().values_list("created_by", flat=True).distinct()
    )


class WormStrainAlleleSearchFieldUserLastname(SearchFieldUserLastnameWithOptions):
    id_list = (
        WormStrainAllele.objects.all().values_list("created_by", flat=True).distinct()
    )


class WormStrainAlleleSearchFieldFormZBaseElement(FieldFormZBaseElement):
    model = WormStrainAllele


class WormStrainAlleleFieldTransgenePlasmids(IntField):
    name = "transgene_plasmids_id"

    def get_lookup_name(self):
        return "transgene_plasmids__id"


class WormStrainAlleleFieldMadeWithPlasmids(IntField):
    name = "made_with_plasmids_id"

    def get_lookup_name(self):
        return "made_with_plasmids__id"


class WormStrainAlleleQLSchema(DjangoQLSchema):
    """Customize search functionality"""

    include = (
        WormStrainAllele,
        User,
    )  # Include only the relevant models to be searched

    def get_fields(self, model):
        """Define fields that can be searched"""

        if model == self.include[0]:
            return [
                "id",
                "lab_identifier",
                "typ_e",
                "transgene",
                "transgene_position",
                WormStrainAlleleFieldTransgenePlasmids(),
                "mutation",
                "mutation_type",
                "mutation_position",
                "reference_strain",
                "made_by_method",
                "made_by_person",
                WormStrainAlleleFieldMadeWithPlasmids(),
                "notes",
                "created_by",
                FieldCreated(),
                FieldLastChanged(),
                FieldFormZBaseElement(),
            ]
        elif model == self.include[1]:
            return [
                WormStrainAlleleSearchFieldUserUsername(),
                WormStrainAlleleSearchFieldUserLastname(),
            ]
        return super().get_fields(model)
