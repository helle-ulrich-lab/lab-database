from django.contrib import admin

from common.export import export_objects

from .export import EColiStrainExportResource


@admin.action(description="Export selected strains")
def export_ecolistrain(modeladmin, request, queryset):
    """Export EColiStrain"""

    export_data = EColiStrainExportResource().export(queryset)
    return export_objects(request, queryset, export_data)
