from django.db.models import CharField
from django.forms import TextInput

from common.admin import (
    AddDocFileInlineMixin,
    DocFileInlineMixin,
)
from formz.actions import formz_as_html

from ..shared.admin import (
    CollectionUserProtectionAdmin,
)
from .actions import export_ecolistrain
from .models import EColiStrainDoc
from .search import EColiStrainQLSchema


class EcoliStrainDocInline(DocFileInlineMixin):
    """Inline to view existing E. coli strain documents"""

    model = EColiStrainDoc


class EColiStrainAddDocInline(AddDocFileInlineMixin):
    """Inline to add new E. coli strain documents"""

    model = EColiStrainDoc


class EColiStrainAdmin(CollectionUserProtectionAdmin):
    list_display = ("id", "name", "resistance", "us_e", "purpose", "approval")
    list_display_links = ("id",)
    list_per_page = 25
    formfield_overrides = {
        CharField: {"widget": TextInput(attrs={"size": "93"})},
    }
    djangoql_schema = EColiStrainQLSchema
    djangoql_completion_enabled_by_default = False
    actions = [export_ecolistrain, formz_as_html]
    search_fields = ["id", "name"]
    autocomplete_fields = ["formz_projects", "sequence_features"]
    inlines = [EcoliStrainDocInline, EColiStrainAddDocInline]
    obj_specific_fields = [
        "name",
        "resistance",
        "genotype",
        "background",
        "supplier",
        "us_e",
        "purpose",
        "note",
        "formz_projects",
        "formz_risk_group",
        "sequence_features",
        "destroyed_date",
    ]
    obj_unmodifiable_fields = [
        "created_date_time",
        "created_approval_by_pi",
        "last_changed_date_time",
        "last_changed_approval_by_pi",
        "created_by",
    ]
    add_view_fieldsets = [
        [
            None,
            {"fields": obj_specific_fields[:8]},
        ],
        [
            "FormZ",
            {
                "classes": tuple(),
                "fields": obj_specific_fields[8:],
            },
        ],
    ]
    change_view_fieldsets = [
        [
            None,
            {"fields": obj_specific_fields[:8] + obj_unmodifiable_fields},
        ],
        [
            "FormZ",
            {
                "classes": (("collapse",)),
                "fields": obj_specific_fields[8:],
            },
        ],
    ]
