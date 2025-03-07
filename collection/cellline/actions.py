from django.contrib import admin

from common.export import export_objects

from .export import CellLineExportResource


@admin.action(description="Export selected cell lines")
def export_cellline(modeladmin, request, queryset):
    """Export CellLine"""

    export_data = CellLineExportResource().export(queryset)
    return export_objects(request, queryset, export_data)
