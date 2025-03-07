from common.admin import AddDocFileInlineMixin, DocFileInlineMixin

from ..shared.admin import CollectionSimpleAdmin
from .actions import export_antibody
from .models import AntibodyDoc
from .search import AntibodyQLSchema


class AntibodyDocInline(DocFileInlineMixin):
    """Inline to view existing Antibody documents"""

    model = AntibodyDoc


class AntibodyAddDocInline(AddDocFileInlineMixin):
    """Inline to add new Antibody documents"""

    model = AntibodyDoc


class AntibodyAdmin(CollectionSimpleAdmin):
    list_display = (
        "id",
        "name",
        "catalogue_number",
        "received_from",
        "species_isotype",
        "clone",
        "l_ocation",
        "get_sheet_short_name",
        "availability",
    )
    list_display_links = ("id",)
    djangoql_schema = AntibodyQLSchema
    actions = [export_antibody]
    search_fields = ["id", "name"]
    inlines = [AntibodyDocInline, AntibodyAddDocInline]
    clone_ignore_fields = ["info_sheet"]
    obj_specific_fields = [
        "name",
        "species_isotype",
        "clone",
        "received_from",
        "catalogue_number",
        "l_ocation",
        "a_pplication",
        "description_comment",
        "info_sheet",
        "availability",
    ]
    obj_unmodifiable_fields = [
        "created_date_time",
        "last_changed_date_time",
    ]
    add_view_fieldsets = [
        [
            None,
            {"fields": obj_specific_fields},
        ],
    ]
    change_view_fieldsets = [
        [
            None,
            {"fields": obj_specific_fields + obj_unmodifiable_fields},
        ],
    ]
