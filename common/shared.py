from django.contrib import admin
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.contrib.admin.utils import unquote
from django.utils.encoding import force_str
from django.utils.text import capfirst
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.urls import re_path
from django.utils.safestring import mark_safe
from django.urls import resolve
import csv
from django.utils import timezone

import xlrd
from django.http import HttpResponse

import os
from functools import reduce
from djangoql.schema import StrField
from simple_history.admin import SimpleHistoryAdmin


class SimpleHistoryWithSummaryAdmin(SimpleHistoryAdmin):

    object_history_template = "admin/object_history_with_change_summary.html"
    history_array_fields = {}

    def history_view(self, request, object_id, extra_context=None):
        """The 'history' admin view for this model."""

        from django.http import Http404

        def pairwise(iterable):
            """ Create pairs of consecutive items from
            iterable"""

            import itertools
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
        
        # If no history was found, see whether this object even exists.
        try:
            obj = self.get_queryset(request).get(**{pk_name: object_id})
        except model.DoesNotExist:
            try:
                obj = action_list.latest('history_date').instance
            except action_list.model.DoesNotExist:
                raise Http404

        ignore_fields = ("time", "_pi", "map_png", "map_gbk", '_user', '_autocomplete')

        # Create data structure for history summary
        history_summary_data = []

        # If more than one history obj, create pairs of history objs
        pairs = pairwise(obj.history.all()) if obj.history.count() > 1 else []

        for newer_hist_obj, older_hist_obj in pairs:

            # Get differences between history obj pairs and add them to a list
            delta = newer_hist_obj.diff_against(older_hist_obj)

            if delta and getattr(delta, 'changes', False):

                changes_list = []

                # Do not show created/changed date/time or approval by PI fields, and png/gbk map fields
                for change in [c for c in delta.changes if not c.field.endswith(ignore_fields)]:

                    field = model._meta.get_field(change.field)
                    field_name = field.verbose_name
                    field_type = field.get_internal_type()

                    if field_type == 'FileField':
                        field_name = field_name.replace(' (.dna)', '') # Remove unwanted characters from field name
                        change_old = os.path.basename(change.old). \
                            replace('.dna', '') if change.old else 'None'
                        change_new = os.path.basename(change.new). \
                            replace('.dna', '') if change.new else 'None'
                    elif field_type == 'ForeignKey':
                        field_model = field.remote_field.model
                        change_old = str(field_model.objects. \
                            get(id=change.old)) if change.old else 'None'
                        change_new = str(field_model.objects. \
                            get(id=change.new)) if change.new else 'None'
                    elif field_type == 'ArrayField':
                        array_field_model = self.history_array_fields.get(change.field, None)
                        if array_field_model:
                            change_old = ', '.join(map(str, array_field_model.objects. \
                                filter(id__in=change.old))) if change.old else 'None'
                            change_new = ', '.join(map(str, array_field_model.objects. \
                                filter(id__in=change.new))) if change.new else 'None'
                        else:
                            change_old = ', '.join(change.old)
                            change_new = ', '.join(change.new)
                    else:
                        change_old = change.old if change.old else 'None'
                        change_new = change.new if change.new else 'None'

                    changes_list.append(
                        (capfirst(field_name), change_old, change_new))

                if changes_list:
                    history_summary_data.append(
                        (newer_hist_obj.last_changed_date_time,
                            User.objects.get(id=int(newer_hist_obj.history_user_id)) if newer_hist_obj.history_user_id else None,
                            changes_list))

        context = self.admin_site.each_context(request)

        context.update({
            'title': _('Change history: %s') % force_str(obj),
            'action_list': action_list,
            'module_name': capfirst(force_str(opts.verbose_name_plural)),
            'object': obj,
            'root_path': getattr(self.admin_site, 'root_path', None),
            'app_label': app_label,
            'opts': opts,
            'history_summary_data': history_summary_data,
            'is_popup': "_popup" in request.GET,
        })
        context.update(extra_context or {})
        extra_kwargs = {}

        return render(request, self.object_history_template, context, **extra_kwargs)


class AdminChangeFormWithNavigation(admin.ModelAdmin):
    
    def get_urls(self):
        """
        Add navigation url
        """

        urls = super(AdminChangeFormWithNavigation, self).get_urls()

        urls = [re_path(r'^(?P<object_id>.+)/navigation/$', view=self.navigation)] + urls
        
        return urls

    def navigation(self, request, *args, **kwargs):

        """Return previous or next record, if available"""

        direction = request.GET.get('direction', None)
        obj_redirect_id = None
        if direction:
            obj_id = int(kwargs['object_id'])
            try:
                if direction.endswith('next'):
                    obj_redirect_id = self.model.objects.filter(id__gt=obj_id).order_by('id').first().id
                else:
                    obj_redirect_id = self.model.objects.filter(id__lt=obj_id).order_by('-id').first().id
            except: 
                    pass
                
        return JsonResponse({'id': obj_redirect_id})

#################################################
#          CUSTOM SEARCH OPTIONS           #
#################################################

class SearchFieldOptUsername(StrField):
    """Create a list of unique users' usernames for search"""

    model = User
    name = 'username'
    suggest_options = True
    id_list = []

    def get_options(self, search):
        """Removes admin, guest and anonymous accounts from 
        the list of options, distinct() returns only unique values
        sorted in alphabetical order"""

        # from https://stackoverflow.com/questions/14907525/how-can-i-chain-djangos-in-and-iexact-queryset-field-lookups/14908214#14908214
        excluded_users = ["AnonymousUser", "guest", "admin"]
        q_list = map(lambda n: Q(username__iexact=n), excluded_users)
        q_list = reduce(lambda a, b: a | b, q_list)

        if self.id_list:
            return self.model.objects.\
            filter(id__in=self.id_list, username__icontains=search).\
            exclude(q_list).\
            distinct().order_by(self.name).\
            values_list(self.name, flat=True)
        else:
            return self.model.objects.\
            filter(username__icontains=search).\
            exclude(q_list).\
            distinct().order_by(self.name).\
            values_list(self.name, flat=True)

class SearchFieldOptLastname(StrField):
    """Create a list of unique user's last names for search"""

    model = User
    name = 'last_name'
    suggest_options = True
    id_list = []

    def get_options(self, search):
        """Removes admin, guest and anonymous accounts from 
        the list of options, distinct() returns only unique values
        sorted in alphabetical order"""

        # from https://stackoverflow.com/questions/14907525/how-can-i-chain-djangos-in-and-iexact-queryset-field-lookups/14908214#14908214
        excluded_users = ["", "admin", "guest"]
        q_list = map(lambda n: Q(last_name__iexact=n), excluded_users)
        q_list = reduce(lambda a, b: a | b, q_list)
        
        if self.id_list:
            return self.model.objects. \
            filter(id__in=self.id_list, last_name__icontains=search).\
            exclude(q_list).\
            distinct().order_by(self.name).\
            values_list(self.name, flat=True)
        else:            
            return self.model.objects. \
            filter(last_name__icontains=search).\
            exclude(q_list).\
            distinct().order_by(self.name).\
            values_list(self.name, flat=True)

#################################################
#               Doc File Inlines                #
#################################################

class DocFileInlineMixin(admin.TabularInline):
    """Inline to view existing documents"""

    verbose_name_plural = "Existing docs"
    extra = 0
    fields = ['description', 'get_doc_short_name', 'comment', 'created_date_time']
    readonly_fields = ['description', 'get_doc_short_name', 'comment', 'created_date_time']

    def get_parent_object(self, request):
        """
        Returns the parent object from the request or None.

        Note that this only works for Inlines, because the `parent_model`
        is not available in the regular admin.ModelAdmin as an attribute.
        """

        resolved = resolve(request.path_info)
        if resolved.kwargs:
            return self.parent_model.objects.get(pk=resolved.kwargs['object_id'])
        return None

    def get_queryset(self, request):

        """Show inline uncollapsed only if docs exist"""
        self.classes = ['collapse',]

        qs = super().get_queryset(request)
        parent_object = self.get_parent_object(request)
        if parent_object:
            filter_params = {f"{self.model._mixin_props.get('parent_field_name')}__pk":
                             parent_object.pk}
            if qs.filter(**filter_params).exists():
                self.classes = []
        return qs

    def has_add_permission(self, request, obj):
        return False

    def get_doc_short_name(self, instance):

        if instance.name and instance.name.name.endswith('pdf'):
            return mark_safe(f'<a class="magnific-popup-iframe-pdflink" href="{instance.name.url}">View PDF</a>')
        return mark_safe(f'<a href="{instance.name.url}">Download</a>')

    get_doc_short_name.short_description = 'Document'

class AddDocFileInlineMixin(admin.TabularInline):
    """Inline to add new documents"""
    
    verbose_name_plural = "New docs"
    extra = 0
    fields = ['description', 'name', 'comment']

    def get_parent_object(self, request):
        """
        Returns the parent object from the request or None.

        Note that this only works for Inlines, because the `parent_model`
        is not available in the regular admin.ModelAdmin as an attribute.
        """

        resolved = resolve(request.path_info)
        if resolved.kwargs:
            return self.parent_model.objects.get(pk=resolved.kwargs['object_id'])
        return None

    def get_queryset(self, request):

        """show inline uncollpased only when adding a new record,
        also return an empty qs"""

        self.classes = ['collapse',]

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
            filtered_inline_instances = [i for i in inline_instances if i.verbose_name_plural != 'Existing docs']

        # Existing objects
        else:
            for inline in inline_instances:
                # Always show existing docs
                if inline.verbose_name_plural == 'Existing docs':
                    filtered_inline_instances.append(inline)
                else:
                    # Do not allow guests to add docs, ever
                    if not request.user.groups.filter(name='Guest').exists():
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
    file_name = f'{queryset.model.__name__}_{now.strftime("%Y%m%d_%H%M%S")}'

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