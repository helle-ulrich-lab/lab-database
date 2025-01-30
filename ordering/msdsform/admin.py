import os

from django.conf import settings
from django.contrib import admin
from django.utils import timezone
from django.utils.safestring import mark_safe
from djangoql.admin import DjangoQLSearchMixin

from .forms import MsdsFormForm
from .search import MsdsFormQLSchema

MEDIA_ROOT = settings.MEDIA_ROOT
LAB_ABBREVIATION_FOR_FILES = getattr(settings, "LAB_ABBREVIATION_FOR_FILES", "")


class MsdsFormAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    list_display = ("id", "pretty_file_name", "view_file_link")
    list_per_page = 25
    ordering = ["label"]
    djangoql_schema = MsdsFormQLSchema
    djangoql_completion_enabled_by_default = False
    search_fields = ["id", "label"]
    form = MsdsFormForm

    @admin.display(description="File name", ordering="label")
    def pretty_file_name(self, instance):
        """Custom file name"""
        return instance.file_name_description

    @admin.display(description="")
    def view_file_link(self, instance):
        """Shows the url of a MSDS form as a HTML <a> tag with text View"""
        return mark_safe(
            '<a class="magnific-popup-iframe-pdflink" href="{}">{}</a>'.format(
                instance.name.url, "View"
            )
        )

    def save_model(self, request, obj, form, change):
        rename = False

        if obj.pk is None:
            rename = True
            obj.label = os.path.basename(obj.name.name)
            obj.save()

        saved_obj = self.model.objects.get(pk=obj.pk)

        # Rename file, if necessary
        if rename or obj.name.name != saved_obj.name.name:
            obj.save()
            obj.label = os.path.basename(obj.name.name)
            new_file_name = os.path.join(
                self.model._model_upload_to,
                f"msds{LAB_ABBREVIATION_FOR_FILES}{obj.id}_"
                f"{timezone.now().strftime('%Y%m%d_%H%M%S_%f')}"
                f"{obj.name.name.split('.')[-1].lower()}",
            )
            new_file_path = os.path.join(MEDIA_ROOT, new_file_name)
            os.rename(obj.name.path, new_file_path)
            obj.name.name = new_file_name

        return super().save_model(request, obj, form, change)

    def add_view(self, request, extra_context=None):
        self.fields = [
            "name",
        ]
        return super().add_view(request)

    def change_view(self, request, object_id, extra_context=None):
        self.fields = ["name", "label"]
        return super().change_view(request, object_id)

    def get_readonly_fields(self, request, obj):
        if obj:
            return [
                "label",
            ]
        else:
            return []
