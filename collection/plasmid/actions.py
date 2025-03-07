from django.contrib import admin

from common.export import export_objects

from .export import PlasmidExportResource


@admin.action(description="Export selected plasmids")
def export_plasmid(modeladmin, request, queryset):
    """Export Plasmid"""

    export_data = PlasmidExportResource().export(queryset)
    return export_objects(request, queryset, export_data)
