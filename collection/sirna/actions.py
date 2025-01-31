from django.contrib import admin

from common.shared import export_objects

from .export import SiRnaExportResource


@admin.action(description="Export selected siRNAs")
def export_si_rna(modeladmin, request, queryset):
    """Export SiRna"""

    export_data = SiRnaExportResource().export(queryset)
    return export_objects(request, queryset, export_data)
