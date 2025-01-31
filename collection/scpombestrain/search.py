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
)
from .models import ScPombeStrain


class ScPombeStrainSearchFieldUserUsername(SearchFieldUserUsernameWithOptions):
    id_list = (
        ScPombeStrain.objects.all().values_list("created_by", flat=True).distinct()
    )


class ScPombeStrainSearchFieldUserLastname(SearchFieldUserLastnameWithOptions):
    id_list = (
        ScPombeStrain.objects.all().values_list("created_by", flat=True).distinct()
    )


class ScPombeStrainFieldEpisomalPlasmidFormZProject(StrField):
    name = "episomal_plasmids_formz_projects_title"
    suggest_options = True

    def get_options(self, search):
        return FormZProject.objects.all().values_list("short_title", flat=True)

    def get_lookup_name(self):
        return "scpombestrainepisomalplasmid__formz_projects__short_title"


class ScPombeStrainQLSchema(DjangoQLSchema):
    """Customize search functionality"""

    include = (ScPombeStrain, User)  # Include only the relevant models to be searched

    def get_fields(self, model):
        """Define fields that can be searched"""

        if model == ScPombeStrain:
            return [
                "id",
                "box_number",
                FieldParent1(),
                FieldParent2(),
                "parental_strain",
                "mating_type",
                "auxotrophic_marker",
                "name",
                FieldIntegratedPlasmidM2M(),
                FieldCassettePlasmidM2M(),
                FieldEpisomalPlasmidM2M(),
                "phenotype",
                "received_from",
                "comment",
                "created_by",
                FieldCreated(),
                FieldLastChanged(),
                FieldFormZProject(),
                ScPombeStrainFieldEpisomalPlasmidFormZProject(),
            ]
        elif model == User:
            return [
                ScPombeStrainSearchFieldUserUsername(),
                ScPombeStrainSearchFieldUserLastname(),
            ]
        return super().get_fields(model)
