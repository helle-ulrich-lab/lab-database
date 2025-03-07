from django.contrib import admin

from common.export import export_objects

from .export import InhibitorExportResource


@admin.action(description="Export selected inhibitors")
def export_inhibitor(modeladmin, request, queryset):
    """Export Inhibitor"""

    export_data = InhibitorExportResource().export(queryset)
    return export_objects(request, queryset, export_data)
