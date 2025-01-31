from django.contrib.auth.models import User
from djangoql.schema import DjangoQLSchema

from common.search import (
    SearchFieldUserLastnameWithOptions,
    SearchFieldUserUsernameWithOptions,
)

from ..shared.admin import (
    FieldCreated,
    FieldLastChanged,
)
from .models import SiRna


class SiRnaSearchFieldUserUsername(SearchFieldUserUsernameWithOptions):
    id_list = SiRna.objects.all().values_list("created_by", flat=True).distinct()


class SiRnaSearchFieldUserLastname(SearchFieldUserLastnameWithOptions):
    id_list = SiRna.objects.all().values_list("created_by", flat=True).distinct()


class SiRnaQLSchema(DjangoQLSchema):
    """Customize search functionality"""

    def get_fields(self, model):
        """Define fields that can be searched"""

        if model == SiRna:
            return [
                "id",
                "name",
                "sequence",
                "sequence_antisense",
                "supplier",
                "supplier_part_no",
                "supplier_si_rna_id",
                "species",
                "target_genes",
                "locus_ids",
                "description_comment",
                "info_sheet",
                "created_by",
                FieldCreated(),
                FieldLastChanged(),
            ]
        elif model == User:
            return [SiRnaSearchFieldUserUsername(), SiRnaSearchFieldUserLastname()]
        return super().get_fields(model)
