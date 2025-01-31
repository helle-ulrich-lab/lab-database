from django.contrib import admin

from common.shared import export_objects

from .export import AntibodyExportResource


@admin.action(description="Export selected antibodies")
def export_antibody(modeladmin, request, queryset):
    """Export Antibody"""

    export_data = AntibodyExportResource().export(queryset)
    return export_objects(request, queryset, export_data)
