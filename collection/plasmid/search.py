from django.contrib.auth import get_user_model
from djangoql.schema import DjangoQLSchema

from common.search import (
    SearchFieldUserLastnameWithOptions,
    SearchFieldUserUsernameWithOptions,
)

from ..shared.admin import (
    FieldCreated,
    FieldFormZProject,
    FieldLastChanged,
    FieldSequenceFeature,
    FieldUse,
)
from .models import Plasmid

User = get_user_model()


class PlasmidSearchFieldUserUsername(SearchFieldUserUsernameWithOptions):
    id_list = Plasmid.objects.all().values_list("created_by", flat=True).distinct()


class PlasmidSearchFieldUserLastname(SearchFieldUserLastnameWithOptions):
    id_list = Plasmid.objects.all().values_list("created_by", flat=True).distinct()


class PlasmidSearchFieldSequenceFeature(FieldSequenceFeature):
    model = Plasmid


class PlasmidQLSchema(DjangoQLSchema):
    """Customize search functionality"""

    include = (Plasmid, User)  # Include only the relevant models to be searched

    def get_fields(self, model):
        """Define fields that can be searched"""

        if model == Plasmid:
            return [
                "id",
                "name",
                "other_name",
                "parent_vector",
                "selection",
                FieldUse(),
                "construction_feature",
                "received_from",
                "note",
                "reference",
                "created_by",
                FieldCreated(),
                FieldLastChanged(),
                PlasmidSearchFieldSequenceFeature(),
                FieldFormZProject(),
            ]
        elif model == User:
            return [PlasmidSearchFieldUserUsername(), PlasmidSearchFieldUserLastname()]
        return super().get_fields(model)
