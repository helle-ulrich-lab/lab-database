from djangoql.schema import DjangoQLSchema

from .models import Inhibitor

from ..shared.admin import FieldLocation


class InhibitorQLSchema(DjangoQLSchema):
    """Customize search functionality for Inhibitor"""

    def get_fields(self, model):
        """Define fields that can be searched"""

        if model == Inhibitor:
            return [
                "id",
                "name",
                "other_names",
                "target",
                "received_from",
                "catalogue_number",
                FieldLocation(),
                "description_comment",
                "info_sheet",
            ]
        return super().get_fields(model)
