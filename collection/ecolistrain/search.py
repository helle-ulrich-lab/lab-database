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
    FieldUse,
)
from .models import EColiStrain

User = get_user_model()


class EColiStrainSearchFieldUserUsername(SearchFieldUserUsernameWithOptions):
    id_list = EColiStrain.objects.all().values_list("created_by", flat=True).distinct()


class EColiStrainSearchFieldUserLastname(SearchFieldUserLastnameWithOptions):
    id_list = EColiStrain.objects.all().values_list("created_by", flat=True).distinct()


class EColiStrainQLSchema(DjangoQLSchema):
    """Customize search functionality"""

    include = (EColiStrain, User)  # Include only the relevant models to be searched

    def get_fields(self, model):
        """Define fields that can be searched"""

        if model == EColiStrain:
            return [
                "id",
                "name",
                "resistance",
                "genotype",
                "supplier",
                FieldUse(),
                "purpose",
                "note",
                "created_by",
                FieldCreated(),
                FieldLastChanged(),
                FieldFormZProject(),
            ]
        elif model == User:
            return [
                EColiStrainSearchFieldUserUsername(),
                EColiStrainSearchFieldUserLastname(),
            ]
        return super().get_fields(model)
