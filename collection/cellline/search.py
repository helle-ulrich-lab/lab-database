from django.contrib.auth.models import User
from djangoql.schema import DjangoQLSchema, IntField, StrField

from common.search import (
    SearchFieldUserLastnameWithOptions,
    SearchFieldUserUsernameWithOptions,
)
from formz.models import Project as FormZProject

from ..shared.admin import (
    FieldCreated,
    FieldEpisomalPlasmidM2M,
    FieldFormZProject,
    FieldIntegratedPlasmidM2M,
    FieldLastChanged,
)
from .models import CellLine


class CellLineSearchFieldParentalCellLineId(IntField):
    name = "parental_line_id"

    def get_lookup_name(self):
        return "parental_line__id"


class CellLineSearchFieldUserUsername(SearchFieldUserUsernameWithOptions):
    id_list = CellLine.objects.all().values_list("created_by", flat=True).distinct()


class CellLineSearchFieldUserLastname(SearchFieldUserLastnameWithOptions):
    id_list = CellLine.objects.all().values_list("created_by", flat=True).distinct()


class CellLineSearchFieldEpisomalPlasmidFormZProject(StrField):
    name = "episomal_plasmids_formz_projects_title"
    suggest_options = True

    def get_options(self, search):
        return FormZProject.objects.all().values_list("short_title", flat=True)

    def get_lookup_name(self):
        return "celllineepisomalplasmid__formz_projects__short_title"


class CellLineQLSchema(DjangoQLSchema):
    """Customize search functionality"""

    include = (CellLine, User)  # Include only the relevant models to be searched

    def get_fields(self, model):
        """Define fields that can be searched"""

        if model == CellLine:
            return [
                "id",
                "name",
                "box_name",
                "alternative_name",
                CellLineSearchFieldParentalCellLineId(),
                "organism",
                "cell_type_tissue",
                "culture_type",
                "growth_condition",
                "freezing_medium",
                "received_from",
                FieldIntegratedPlasmidM2M(),
                FieldEpisomalPlasmidM2M(),
                "description_comment",
                "created_by",
                FieldCreated(),
                FieldLastChanged(),
                FieldFormZProject(),
                CellLineSearchFieldEpisomalPlasmidFormZProject(),
            ]
        elif model == User:
            return [
                CellLineSearchFieldUserUsername(),
                CellLineSearchFieldUserLastname(),
            ]
        return super().get_fields(model)
