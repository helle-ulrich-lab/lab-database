from djangoql.schema import DjangoQLSchema

from ..shared.admin import (
    FieldApplication,
    FieldLocation,
)
from .models import Antibody


class AntibodyQLSchema(DjangoQLSchema):
    """Customize search functionality for Antibody"""

    def get_fields(self, model):
        """Define fields that can be searched"""

        if model == Antibody:
            return [
                "id",
                "name",
                "species_isotype",
                "clone",
                "received_from",
                "catalogue_number",
                "info_sheet",
                FieldLocation(),
                FieldApplication(),
                "description_comment",
                "info_sheet",
                "availability",
            ]
        return super().get_fields(model)
