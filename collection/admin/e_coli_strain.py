from django.contrib import admin
from django.contrib.auth.models import User
from django.db.models import CharField
from django.forms import TextInput
from djangoql.schema import DjangoQLSchema
from import_export import resources

from collection.admin.shared import (
    CollectionUserProtectionAdmin,
    FieldCreated,
    FieldFormZProject,
    FieldLastChanged,
    FieldUse,
    formz_as_html,
)
from collection.models import EColiStrain, EColiStrainDoc
from common.shared import (
    AddDocFileInlineMixin,
    DocFileInlineMixin,
    SearchFieldOptLastname,
    SearchFieldOptUsername,
    export_objects,
)
from formz.models import FormZBaseElement, FormZProject


class SearchFieldOptUsernameEColi(SearchFieldOptUsername):
    id_list = EColiStrain.objects.all().values_list("created_by", flat=True).distinct()


class SearchFieldOptLastnameEColi(SearchFieldOptLastname):
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
            return [SearchFieldOptUsernameEColi(), SearchFieldOptLastnameEColi()]
        return super().get_fields(model)


class EColiStrainExportResource(resources.ModelResource):
    """Defines a custom export resource class for EColiStrain"""

    class Meta:
        model = EColiStrain
        fields = (
            "id",
            "name",
            "resistance",
            "genotype",
            "supplier",
            "us_e",
            "purpose",
            "note",
            "created_date_time",
            "created_by__username",
        )
        export_order = fields


@admin.action(description="Export selected strains")
def export_ecolistrain(modeladmin, request, queryset):
    """Export EColiStrain"""

    export_data = EColiStrainExportResource().export(queryset)
    return export_objects(request, queryset, export_data)


class EcoliStrainDocInline(DocFileInlineMixin):
    """Inline to view existing E. coli strain documents"""

    model = EColiStrainDoc


class EColiStrainAddDocInline(AddDocFileInlineMixin):
    """Inline to add new E. coli strain documents"""

    model = EColiStrainDoc


class EColiStrainPage(CollectionUserProtectionAdmin):
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
    autocomplete_fields = ["formz_projects", "formz_elements"]
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
        "formz_elements",
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
    history_array_fields = {
        "history_formz_projects": FormZProject,
        "history_formz_elements": FormZBaseElement,
        "history_documents": EColiStrainDoc,
    }
