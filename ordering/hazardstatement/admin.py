from django.contrib import admin


class HazardStatementAdmin(admin.ModelAdmin):
    list_display = ("code", "description", "is_cmr")
    list_display_links = ("code",)
    list_per_page = 25
    ordering = ["code"]
    search_fields = ["code"]
