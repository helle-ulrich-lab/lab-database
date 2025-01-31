from django.contrib import admin

from common.shared import export_objects

from .export import WormStrainAlleleExportResource, WormStrainExportResource


@admin.action(description="Export selected strains")
def export_wormstrain(modeladmin, request, queryset):
    """Export WormStrain"""

    export_data = WormStrainExportResource().export(queryset)
    return export_objects(request, queryset, export_data)


@admin.action(description="Export selected worm strain alleles")
def export_wormstrainallele(modeladmin, request, queryset):
    """Export WormStrainAllele"""

    export_data = WormStrainAlleleExportResource().export(queryset)
    return export_objects(request, queryset, export_data)
