from django.contrib import admin

from common.export import export_objects

from .export import OligoExportResource


@admin.action(description="Export selected oligos")
def export_oligo(modeladmin, request, queryset):
    """Export Oligo"""

    export_data = OligoExportResource().export(queryset)
    return export_objects(request, queryset, export_data)
