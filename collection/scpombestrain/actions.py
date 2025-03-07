from django.contrib import admin

from common.export import export_objects

from .export import ScPombeStrainExportResource


@admin.action(description="Export selected strains")
def export_scpombestrain(modeladmin, request, queryset):
    """Export ScPombeStrain"""

    export_data = ScPombeStrainExportResource().export(queryset)
    return export_objects(request, queryset, export_data)
