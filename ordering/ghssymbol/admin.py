from django.contrib import admin
from django.utils.safestring import mark_safe


class GhsSymbolAdmin(admin.ModelAdmin):
    list_display = ("code", "pictogram_img", "description")
    list_display_links = ("code",)
    list_per_page = 25
    ordering = ["code"]
    search_fields = ["code"]

    @admin.display(description="Pictogram")
    def pictogram_img(self, instance):
        return mark_safe(
            f'<img style="max-height:60px;" src="{instance.pictogram.url}" />'
        )
