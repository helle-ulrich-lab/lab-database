from django.contrib import admin
from djangoql.schema import DjangoQLSchema
from import_export import resources

from collection.admin.shared import CollectionSimpleAdmin, FieldLocation
from collection.models import Inhibitor, InhibitorDoc
from common.shared import AddDocFileInlineMixin, DocFileInlineMixin, export_objects


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


class InhibitorExportResource(resources.ModelResource):
    """Custom export resource class for Inhibitor"""

    class Meta:
        model = Inhibitor
        fields = (
            "id",
            "name",
            "other_names",
            "target",
            "received_from",
            "catalogue_number",
            "l_ocation",
            "ic50",
            "amount",
            "stock_solution",
            "description_comment",
            "info_sheet",
        )
        export_order = fields


@admin.action(description="Export selected inhibitors")
def export_inhibitor(modeladmin, request, queryset):
    """Export Inhibitor"""

    export_data = InhibitorExportResource().export(queryset)
    return export_objects(request, queryset, export_data)


class InhibitorDocInline(DocFileInlineMixin):
    """Inline to view existing Inhibitor documents"""

    model = InhibitorDoc


class InhibitorAddDocInline(AddDocFileInlineMixin):
    """Inline to add new Inhibitor documents"""

    model = InhibitorDoc


class InhibitorPage(CollectionSimpleAdmin):

    list_display = (
        "id",
        "name",
        "target",
        "catalogue_number",
        "received_from",
        "l_ocation",
        "get_sheet_short_name",
    )
    list_display_links = ("id",)
    djangoql_schema = InhibitorQLSchema
    actions = [export_inhibitor]
    search_fields = ["id", "name"]
    inlines = [InhibitorDocInline, InhibitorAddDocInline]
    clone_ignore_fields = ["info_sheet"]
    obj_specific_fields = [
        "name",
        "other_names",
        "target",
        "received_from",
        "catalogue_number",
        "l_ocation",
        "ic50",
        "amount",
        "stock_solution",
        "description_comment",
        "info_sheet",
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
    history_array_fields = {"history_documents": InhibitorDoc}
