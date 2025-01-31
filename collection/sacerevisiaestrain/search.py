from django.contrib.auth.models import User
from djangoql.schema import DjangoQLSchema, StrField

from common.search import (
    SearchFieldUserLastnameWithOptions,
    SearchFieldUserUsernameWithOptions,
)
from formz.models import FormZProject

from ..shared.admin import (
    FieldCassettePlasmidM2M,
    FieldCreated,
    FieldEpisomalPlasmidM2M,
    FieldFormZProject,
    FieldIntegratedPlasmidM2M,
    FieldLastChanged,
    FieldParent1,
    FieldParent2,
    FieldUse,
)
from .models import SaCerevisiaeStrain


class SaCerevisiaeStrainSearchFieldUserUsername(SearchFieldUserUsernameWithOptions):
    id_list = (
        SaCerevisiaeStrain.objects.all().values_list("created_by", flat=True).distinct()
    )


class SaCerevisiaeStrainSearchFieldUserLastname(SearchFieldUserLastnameWithOptions):
    id_list = (
        SaCerevisiaeStrain.objects.all().values_list("created_by", flat=True).distinct()
    )


class SaCerevisiaeStrainSearchFieldEpisomalPlasmidFormZProject(StrField):
    name = "episomal_plasmids_formz_projects_title"
    suggest_options = True

    def get_options(self, search):
        return FormZProject.objects.all().values_list("short_title", flat=True)

    def get_lookup_name(self):
        return "sacerevisiaestrainepisomalplasmid__formz_projects__short_title"


class SaCerevisiaeStrainQLSchema(DjangoQLSchema):
    """Customize search functionality"""

    include = (
        SaCerevisiaeStrain,
        User,
    )  # Include only the relevant models to be searched

    def get_fields(self, model):
        """Define fields that can be searched"""

        if model == SaCerevisiaeStrain:
            return [
                "id",
                "name",
                "relevant_genotype",
                "mating_type",
                "chromosomal_genotype",
                FieldParent1(),
                FieldParent2(),
                "parental_strain",
                "construction",
                "modification",
                FieldIntegratedPlasmidM2M(),
                FieldCassettePlasmidM2M(),
                FieldEpisomalPlasmidM2M(),
                "plasmids",
                "selection",
                "phenotype",
                "background",
                "received_from",
                FieldUse(),
                "note",
                "reference",
                "created_by",
                FieldCreated(),
                FieldLastChanged(),
                FieldFormZProject(),
                SaCerevisiaeStrainSearchFieldEpisomalPlasmidFormZProject(),
            ]
        elif model == User:
            return [
                SaCerevisiaeStrainSearchFieldUserUsername(),
                SaCerevisiaeStrainSearchFieldUserLastname(),
            ]
        return super().get_fields(model)
