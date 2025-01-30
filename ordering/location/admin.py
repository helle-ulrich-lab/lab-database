from django.contrib import admin


class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "status")
    list_display_links = ("name",)
    list_per_page = 25
    ordering = ["name"]
