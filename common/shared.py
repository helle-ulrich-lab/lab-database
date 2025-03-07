import csv
import itertools

import xlrd
from django.contrib import admin
from django.contrib.admin.utils import unquote
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import path, resolve
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.safestring import mark_safe
from django.utils.text import capfirst
from django.utils.translation import gettext_lazy as _
from simple_history.admin import SimpleHistoryAdmin


class SimpleHistoryWithSummaryAdmin(SimpleHistoryAdmin):
    object_history_template = "admin/object_history_with_change_summary.html"
    history_array_fields = {}

    def history_view(self, request, object_id, extra_context=None):
        """The 'history' admin view for this model."""

        def pairwise(iterable):
            """Create pairs of consecutive items from
            iterable"""

            a, b = itertools.tee(iterable)
            next(b, None)
            return zip(a, b)

        request.current_app = self.admin_site.name
        model = self.model
        opts = model._meta
        app_label = opts.app_label
        pk_name = opts.pk.attname
        history = getattr(model, model._meta.simple_history_manager_attribute)
        object_id = unquote(object_id)
        action_list = history.filter(**{pk_name: object_id})

        # If no history was found, see whether this object even exists
        try:
            obj = self.get_queryset(request).get(**{pk_name: object_id})
        except model.DoesNotExist:
            try:
                obj = action_list.latest("history_date").instance
            except action_list.model.DoesNotExist:
                raise Http404

        context = self.admin_site.each_context(request)
        context.update(
            {
                "title": _("Change history: %s") % force_str(obj),
                "action_list": action_list,
                "module_name": capfirst(force_str(opts.verbose_name_plural)),
                "object": obj,
                "root_path": getattr(self.admin_site, "root_path", None),
                "app_label": app_label,
                "opts": opts,
                "is_popup": "_popup" in request.GET,
            }
        )
        context.update(extra_context or {})
        extra_kwargs = {}

        return render(request, self.object_history_template, context, **extra_kwargs)


class AdminChangeFormWithNavigation(admin.ModelAdmin):
    def get_urls(self):
        """
        Add navigation url
        """

        urls = super().get_urls()

        urls = [path("<path:object_id>/navigation/", view=self.navigation)] + urls

        return urls

    def navigation(self, request, *args, **kwargs):
        """Return previous or next record, if available"""

        direction = request.GET.get("direction", None)
        obj_redirect_id = None
        if direction:
            obj_id = int(kwargs["object_id"])
            try:
                if direction.endswith("next"):
                    obj_redirect_id = (
                        self.model.objects.filter(id__gt=obj_id)
                        .order_by("id")
                        .first()
                        .id
                    )
                else:
                    obj_redirect_id = (
                        self.model.objects.filter(id__lt=obj_id)
                        .order_by("-id")
                        .first()
                        .id
                    )
            except:
                pass

        return JsonResponse({"id": obj_redirect_id})


#################################################
#               Doc File Inlines                #
#################################################


class DocFileInlineMixin(admin.TabularInline):
    """Inline to view existing documents"""

    verbose_name_plural = "Existing docs"
    extra = 0
    fields = ["description", "get_doc_short_name", "comment", "created_date_time"]
    readonly_fields = [
        "description",
        "get_doc_short_name",
        "comment",
        "created_date_time",
    ]

    def get_parent_object(self, request):
        """
        Returns the parent object from the request or None.

        Note that this only works for Inlines, because the `parent_model`
        is not available in the regular admin.ModelAdmin as an attribute.
        """

        resolved = resolve(request.path_info)
        if resolved.kwargs:
            return self.parent_model.objects.get(pk=resolved.kwargs["object_id"])
        return None

    def get_queryset(self, request):
        """Show inline uncollapsed only if docs exist"""
        self.classes = [
            "collapse",
        ]

        qs = super().get_queryset(request)
        parent_object = self.get_parent_object(request)
        if parent_object:
            filter_params = {
                f"{self.model._mixin_props.get('parent_field_name')}__pk": parent_object.pk
            }
            if qs.filter(**filter_params).exists():
                self.classes = []
        return qs

    def has_add_permission(self, request, obj):
        return False

    @admin.display(description="Document")
    def get_doc_short_name(self, instance):
        if instance.name and instance.name.name.endswith("pdf"):
            return mark_safe(
                f'<a class="magnific-popup-iframe-pdflink" href="{instance.name.url}">View PDF</a>'
            )
        return mark_safe(f'<a href="{instance.name.url}">Download</a>')


class AddDocFileInlineMixin(admin.TabularInline):
    """Inline to add new documents"""

    verbose_name_plural = "New docs"
    extra = 0
    fields = ["description", "name", "comment"]

    def get_parent_object(self, request):
        """
        Returns the parent object from the request or None.

        Note that this only works for Inlines, because the `parent_model`
        is not available in the regular admin.ModelAdmin as an attribute.
        """

        resolved = resolve(request.path_info)
        if resolved.kwargs:
            return self.parent_model.objects.get(pk=resolved.kwargs["object_id"])
        return None

    def get_queryset(self, request):
        """show inline uncollpased only when adding a new record,
        also return an empty qs"""

        self.classes = [
            "collapse",
        ]

        parent_object = self.get_parent_object(request)
        if not parent_object:
            self.classes = []
        return self.model.objects.none()

    def has_change_permission(self, request, obj=None):
        return False


class ToggleDocInlineMixin(admin.ModelAdmin):
    def get_inline_instances(self, request, obj=None):
        inline_instances = super().get_inline_instances(request, obj)
        filtered_inline_instances = []

        # New objects
        if not obj:
            filtered_inline_instances = [
                i for i in inline_instances if i.verbose_name_plural != "Existing docs"
            ]

        # Existing objects
        else:
            for inline in inline_instances:
                # Always show existing docs
                if inline.verbose_name_plural == "Existing docs":
                    filtered_inline_instances.append(inline)
                else:
                    # Do not allow guests to add docs, ever
                    if not request.user.groups.filter(name="Guest").exists():
                        filtered_inline_instances.append(inline)

        return filtered_inline_instances

    # def get_formsets_with_inlines(self, request, obj=None):
    #     """Remove DocInline from add/change form if user who
    #     created a  object is not the request user a lab manager
    #     or a superuser"""

    #     # New objects
    #     if not obj:
    #         for inline in self.get_inline_instances(request, obj):
    #             # Do not show DocFileInlineMixin for new objetcs
    #             if inline.verbose_name_plural == 'Existing docs':
    #                 continue
    #             else:
    #                 yield inline.get_formset(request, obj), inline

    #     # Existing objects
    #     else:
    #         for inline in self.get_inline_instances(request, obj):
    #             # Always show existing docs
    #             if inline.verbose_name_plural == 'Existing docs':
    #                 yield inline.get_formset(request, obj), inline
    #             else:
    #                 # Do not allow guests to add docs, ever
    #                 if not request.user.groups.filter(name='Guest').exists():
    #                     yield inline.get_formset(request, obj), inline


def export_objects(request, queryset, export_data):
    file_format = request.POST.get("format", default="none")
    now = timezone.localtime(timezone.now())
    file_name = f"{queryset.model.__name__}_{now.strftime('%Y%m%d_%H%M%S')}"

    # Excel file
    if file_format == "xlsx":
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="{file_name}.xlsx'
        response.write(export_data.xlsx)

    # TSV file
    elif file_format == "tsv":
        response = HttpResponse(content_type="text/tab-separated-values")
        response["Content-Disposition"] = f'attachment; filename="{file_name}.tsv'
        xlsx_file = xlrd.open_workbook(file_contents=export_data.xlsx)
        sheet = xlsx_file.sheet_by_index(0)
        wr = csv.writer(response, delimiter="\t")
        # Get rid of return chars
        for rownum in range(sheet.nrows):
            row_values = [
                str(i).replace("\n", "").replace("\r", "").replace("\t", "")
                for i in sheet.row_values(rownum)
            ]
            wr.writerow(row_values)

    return response


def save_history_fields(admin_instance, obj, history_obj):
    history_array_fields = obj._history_array_fields.copy()
    if admin_instance.m2m_save_ignore_fields:
        history_array_fields = {
            k: v
            for k, v in history_array_fields.items()
            if k not in admin_instance.m2m_save_ignore_fields
        }

    # Keep a record of the IDs of linked M2M fields in the main obj record
    # Not pretty, but it works

    for m2m_history_field_name, m2m_model in history_array_fields.items():
        try:
            m2m_set = getattr(obj, f"{m2m_history_field_name[8:]}")
        except Exception:
            try:
                m2m_set = getattr(obj, f"{m2m_model._meta.model_name}_set")
            except Exception:
                continue
        setattr(
            obj,
            m2m_history_field_name,
            (
                list(m2m_set.order_by("id").distinct("id").values_list("id", flat=True))
                if m2m_set.exists()
                else []
            ),
        )

    obj.save_without_historical_record()

    if history_obj:
        for (
            m2m_history_field_name,
            m2m_model,
        ) in obj._history_array_fields.items():
            setattr(
                history_obj,
                m2m_history_field_name,
                getattr(obj, m2m_history_field_name),
            )

        history_obj.save()
