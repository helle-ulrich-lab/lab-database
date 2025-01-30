from django.contrib import admin
from django.contrib.auth.models import User
from django_better_admin_arrayfield.admin.mixins import DynamicArrayMixin
from djangoql.schema import DjangoQLSchema
from import_export import resources
from import_export.fields import Field

from collection.admin.shared import (
    CollectionSimpleAdmin,
    FieldCreated,
    FieldLastChanged,
)
from collection.models import SiRna, SiRnaDoc
from common.search import (
    SearchCustomFieldUserLastnameWithOptions,
    SearchCustomFieldUserUsernameWithOptions,
)
from common.shared import (
    AddDocFileInlineMixin,
    DocFileInlineMixin,
    export_objects,
)
from formz.models import Species
from ordering.models import Order


class SearchFieldOptUsernameSiRna(SearchCustomFieldUserUsernameWithOptions):
    id_list = SiRna.objects.all().values_list("created_by", flat=True).distinct()


class SearchFieldOptLastnameSiRna(SearchCustomFieldUserLastnameWithOptions):
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
            return [SearchFieldOptUsernameSiRna(), SearchFieldOptLastnameSiRna()]
        return super().get_fields(model)


class SiRnaExportResource(resources.ModelResource):
    """Defines a custom export resource class for SiRna"""

    species_name = Field()

    def dehydrate_species_name(self, si_rna):
        return str(si_rna.species)

    class Meta:
        model = SiRna
        fields = (
            "id",
            "name",
            "sequence",
            "sequence_antisense",
            "supplier",
            "supplier_part_no",
            "supplier_si_rna_id",
            "species_name",
            "target_genes",
            "locus_ids",
            "description_comment",
            "info_sheet",
            "orders",
            "created_date_time",
            "created_by__username",
        )
        export_order = fields


@admin.action(description="Export selected siRNAs")
def export_si_rna(modeladmin, request, queryset):
    """Export SiRna"""

    export_data = SiRnaExportResource().export(queryset)
    return export_objects(request, queryset, export_data)


class InhibitorDocInline(DocFileInlineMixin):
    """Inline to view existing Inhibitor documents"""

    model = SiRnaDoc


class InhibitorAddDocInline(AddDocFileInlineMixin):
    """Inline to add new Inhibitor documents"""

    model = SiRnaDoc


class SiRnaPage(
    DynamicArrayMixin,
    CollectionSimpleAdmin,
):
    list_display = (
        "id",
        "name",
        "sequence",
        "supplier",
        "supplier_part_no",
        "target_genes",
        "get_sheet_short_name",
        "created_by",
    )
    list_display_links = ("id",)
    djangoql_schema = SiRnaQLSchema
    actions = [export_si_rna]
    search_fields = ["id", "name"]
    autocomplete_fields = ["created_by", "orders"]
    inlines = [InhibitorDocInline, InhibitorAddDocInline]
    clone_ignore_fields = ["info_sheet"]
    obj_specific_fields = [
        "name",
        "sequence",
        "sequence_antisense",
        "species",
        "target_genes",
        "locus_ids",
        "description_comment",
        "info_sheet",
        "supplier",
        "supplier_part_no",
        "supplier_si_rna_id",
        "orders",
    ]
    obj_unmodifiable_fields = [
        "created_date_time",
        "last_changed_date_time",
        "created_by",
    ]
    add_view_fieldsets = [
        [
            None,
            {
                "fields": obj_specific_fields[:8]
                + [
                    "created_by",
                ]
            },
        ],
        ["Supplier information", {"fields": obj_specific_fields[8:]}],
    ]
    change_view_fieldsets = [
        [None, {"fields": obj_specific_fields[:8] + obj_unmodifiable_fields}],
        ["Supplier information", {"fields": obj_specific_fields[8:]}],
    ]
    history_array_fields = {"history_orders": Order, "history_documents": SiRnaDoc}

    def add_view(self, request, form_url="", extra_context=None):
        if "created_by" in self.obj_unmodifiable_fields:
            self.obj_unmodifiable_fields.remove("created_by")

        return super().add_view(request, form_url, extra_context)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        if "created_by" not in self.obj_unmodifiable_fields:
            self.obj_unmodifiable_fields = self.obj_unmodifiable_fields + ["created_by"]

        return super().change_view(request, object_id, form_url, extra_context)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        try:
            request.resolver_match.args[0]
        except Exception:
            # Exclude certain users from the 'Created by' field in the order form
            if db_field.name == "created_by":
                if (
                    request.user.is_superuser
                    or request.user.groups.filter(name="Lab manager").exists()
                ):
                    kwargs["queryset"] = User.objects.exclude(
                        username__in=["admin", "guest", "AnonymousUser"]
                    ).order_by("last_name")
                kwargs["initial"] = request.user.id

            # Only show species that have been set to be shown in cell line collection
            if db_field.name == "species":
                kwargs["queryset"] = Species.objects.filter(
                    show_in_cell_line_collection=True
                )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)
