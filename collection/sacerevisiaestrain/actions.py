from django.contrib import admin

from common.shared import export_objects

from .export import SaCerevisiaeStrainExportResource


@admin.action(description="Export selected strains")
def export_sacerevisiaestrain(modeladmin, request, queryset):
    """Export SaCerevisiaeStrain"""

    export_data = SaCerevisiaeStrainExportResource().export(queryset)
    return export_objects(request, queryset, export_data)
