from django.contrib import admin


class SignalWordAdmin(admin.ModelAdmin):
    list_display = ("signal_word",)
    list_display_links = ("signal_word",)
    list_per_page = 25
    ordering = ["signal_word"]
    search_fields = ["signal_word"]
