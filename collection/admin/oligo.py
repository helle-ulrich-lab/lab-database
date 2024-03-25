from django.http import HttpResponse
from django.forms import TextInput
from django.db.models import CharField
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.http import HttpResponseRedirect
from django.utils.html import format_html
from django.contrib import messages
from django import forms
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import FieldError, ValidationError
from django.db import DataError
from django.db.models.functions import Collate
from django.db import models

from djangoql.schema import DjangoQLSchema
from djangoql.schema import StrField
from djangoql.exceptions import DjangoQLError
from djangoql.parser import DjangoQLParser
from djangoql.queryset import build_filter

from djangoql.admin import DjangoQLSearchMixin
from import_export import resources

import xlrd
import csv
from datetime import datetime
from urllib.parse import quote as urlquote
import os

from django.conf import settings
MEDIA_ROOT = settings.MEDIA_ROOT
LAB_ABBREVIATION_FOR_FILES = getattr(settings, 'LAB_ABBREVIATION_FOR_FILES', '')

from common.shared import SimpleHistoryWithSummaryAdmin
from common.shared import AdminChangeFormWithNavigation
from common.shared import SearchFieldOptUsername
from common.shared import SearchFieldOptLastname
from common.shared import DocFileInlineMixin
from common.shared import AddDocFileInlineMixin
from collection.admin.shared import FieldCreated
from collection.admin.shared import FieldLastChanged
from collection.admin.shared import Approval
from collection.admin.shared import FieldUse

from collection.models.oligo import Oligo
from collection.models.oligo import OligoDoc
from common.shared import ToggleDocInlineMixin
from formz.models import FormZBaseElement


class SearchFieldOptUsernameOligo(SearchFieldOptUsername):

    id_list = Oligo.objects.all().values_list('created_by', flat=True).distinct()

class SearchFieldOptLastnameOligo(SearchFieldOptLastname):

    id_list = Oligo.objects.all().values_list('created_by', flat=True).distinct()

class OligoSequence(StrField):
    
    name = 'sequence'

    def get_lookup(self, path, operator, value):

        """Override parent's method to include deterministic
        collation flag to lookup for sequence"""

        search = '__'.join(path + [self.get_lookup_name()])
        search = search.replace('sequence', 'sequence_deterministic') if 'sequence' in search else search
        op, invert = self.get_operator(operator)
        q = models.Q(**{'%s%s' % (search, op): self.get_lookup_value(value)})
        return ~q if invert else q

class OligoQLSchema(DjangoQLSchema):
    '''Customize search functionality'''
    
    include = (Oligo, User) # Include only the relevant models to be searched
    
    def get_fields(self, model):
        '''Define fields that can be searched'''
        
        if model == Oligo:
            return ['id', 'name', OligoSequence(), 'length', FieldUse(), 'gene', 'restriction_site', 
                    'description', 'comment', 'created_by', FieldCreated(), FieldLastChanged(),]
        elif model == User:
            return [SearchFieldOptUsernameOligo(), SearchFieldOptLastnameOligo()]
        return super(OligoQLSchema, self).get_fields(model)

class OligoExportResource(resources.ModelResource):
    """Defines a custom export resource class for Oligo"""
    
    class Meta:
        model = Oligo
        fields = ('id', 'name','sequence', 'us_e', 'gene', 'restriction_site', 'description', 'comment',
        'created_date_time', 'created_by__username',)

def export_oligo(modeladmin, request, queryset):
    """Export Oligo"""

    export_data = OligoExportResource().export(queryset)

    file_format = request.POST.get('format', default='xlsx')

    if file_format == 'xlsx':
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="{}_{}_{}.xlsx'.format(queryset.model.__name__, datetime.now().strftime("%Y%m%d"), datetime.now().strftime("%H%M%S"))
        response.write(export_data.xlsx)
    elif file_format == 'tsv':
        response = HttpResponse(content_type='text/tab-separated-values')
        response['Content-Disposition'] = 'attachment; filename="{}_{}_{}.tsv'.format(queryset.model.__name__, datetime.now().strftime("%Y%m%d"), datetime.now().strftime("%H%M%S"))
        xlsx_file = xlrd.open_workbook(file_contents=export_data.xlsx)
        sheet = xlsx_file.sheet_by_index(0)
        wr = csv.writer(response, delimiter="\t")
        for rownum in range(sheet.nrows):
            row_values = [str(i).replace("\n", "").replace('\r', '').replace("\t", "") for i in sheet.row_values(rownum)]
            wr.writerow(row_values)
    return response
export_oligo.short_description = "Export selected oligos"

class OligoForm(forms.ModelForm):
    
    class Meta:
        model = Oligo
        fields = '__all__'

    def clean_sequence(self):
        """Check if sequence is unique before saving"""

        sequence = self.cleaned_data["sequence"]
        qs = Oligo.objects.filter(sequence=sequence)
        
        if not self.instance.pk:
            if qs.exists():
                raise forms.ValidationError('Oligo with this Sequence already exists.')
        else:
            if qs.exclude(id=self.instance.pk).exists():
                raise forms.ValidationError('Oligo with this Sequence already exists.')
        
        return sequence

    def clean_name(self):
        """Check if name is unique before saving"""

        name = self.cleaned_data["name"]
        qs = Oligo.objects.filter(name=name)
        
        if not self.instance.pk:
            if qs.exists():
                raise forms.ValidationError('Oligo with this Name already exists.')
        else:
            if qs.exclude(id=self.instance.pk).exists():
                raise forms.ValidationError('Oligo with this Name already exists.')
        
        return name

class OligoDjangoQLSearchMixin(DjangoQLSearchMixin):

    def get_search_results(self, request, queryset, search_term):

        """
            Override parent's method to filter sequence using a non
            deterministic collaction
        """

        def apply_search(queryset, search, schema=None):
            ast = DjangoQLParser().parse(search)
            schema = schema or DjangoQLSchema
            schema_instance = schema(queryset.model)
            schema_instance.validate(ast)
            filter_params = build_filter(ast, schema_instance)
            if any(n[0].startswith('sequence') for n in filter_params.deconstruct()[1]):
                return queryset.annotate(sequence_deterministic=Collate("sequence", "und-x-icu")).filter(filter_params)
            return queryset.filter(filter_params)

        if (
            self.search_mode_toggle_enabled() and
            not self.djangoql_search_enabled(request)
        ):
            return super(DjangoQLSearchMixin, self).get_search_results(
                request=request,
                queryset=queryset,
                search_term=search_term,
            )
        use_distinct = False
        if not search_term:
            return queryset, use_distinct

        try:
            qs = apply_search(queryset, search_term, self.djangoql_schema)
        except (DjangoQLError, ValueError, FieldError, ValidationError) as e:
            msg = self.djangoql_error_message(e)
            messages.add_message(request, messages.WARNING, msg)
            qs = queryset.none()
        else:
            # Hack to handle 'inet' comparison errors in Postgres. If you
            # know a better way to check for such an error, please submit a PR.
            try:
                # Django >= 2.1 has built-in .explain() method
                explain = getattr(qs, 'explain', None)
                if callable(explain):
                    explain()
                else:
                    list(qs[:1])
            except DataError as e:
                if 'inet' not in str(e):
                    raise
                msg = self.djangoql_error_message(e)
                messages.add_message(request, messages.WARNING, msg)
                qs = queryset.none()

        return qs, use_distinct

class OligoDocInline(DocFileInlineMixin):
    """Inline to view existing Oligo documents"""

    model = OligoDoc

class OligoAddDocInline(AddDocFileInlineMixin):
    """Inline to add new Oligo documents"""

    model = OligoDoc

class OligoPage(ToggleDocInlineMixin, OligoDjangoQLSearchMixin,
                SimpleHistoryWithSummaryAdmin, Approval,
                AdminChangeFormWithNavigation):
    list_display = ('id', 'name','get_oligo_short_sequence', 'restriction_site','created_by', 'approval')
    list_display_links = ('id',)
    list_per_page = 25
    formfield_overrides = {
    CharField: {'widget': TextInput(attrs={'size':'93'})},} # Make TextInput fields wider
    djangoql_schema = OligoQLSchema
    djangoql_completion_enabled_by_default = False
    actions = [export_oligo]
    search_fields = ['id', 'name']
    autocomplete_fields = ['formz_elements']
    form = OligoForm
    inlines = [OligoDocInline, OligoAddDocInline]

    def get_oligo_short_sequence(self, instance):
        '''This function allows you to define a custom field for the list view to
        be defined in list_display as the name of the function, e.g. in this case
        list_display = ('id', 'name', )'''
        
        if instance.sequence:
            if len(instance.sequence) <= 75:
                return instance.sequence
            else:
                return instance.sequence[0:75] + "..."
    get_oligo_short_sequence.short_description = 'Sequence'

    def save_model(self, request, obj, form, change):
        '''Override default save_model to limit a user's ability to save a record
        Superusers and lab managers can change all records
        Regular users can change only their own records
        Guests cannot change any record'''

        rename_doc = False
        new_obj = False

        if obj.pk == None:
            
            obj.id = Oligo.objects.order_by('-id').first().id + 1 if Oligo.objects.exists() else 1
            obj.created_by = request.user
            if obj.info_sheet:
                rename_doc = True
                new_obj = True
            obj.save()

            # If the request's user is the principal investigator, approve the record
            # right away. If not, create an approval record
            if request.user.labuser.is_principal_investigator:
                original_last_changed_date_time = obj.last_changed_date_time
                obj.created_approval_by_pi = True
                obj.approval_by_pi_date_time = timezone.now()
                obj.save_without_historical_record()
                Oligo.objects.filter(id=obj.pk).update(last_changed_date_time=original_last_changed_date_time)
            else:
                obj.approval.create(activity_type='created', activity_user=request.user)
            
        else:

            # Check if the disapprove button was clicked. If so, and no approval
            # record for the object exists, create one
            if "_disapprove_record" in request.POST:
                if not obj.approval.all():
                    original_last_changed_date_time = obj.last_changed_date_time
                    obj.approval.create(activity_type='changed', activity_user=obj.created_by)
                    obj.last_changed_approval_by_pi = False
                    obj.save_without_historical_record()
                    Oligo.objects.filter(id=obj.pk).update(last_changed_date_time=original_last_changed_date_time)
                return

            # if self.can_change:

            # Approve right away if the request's user is the principal investigator. If not,
            # create an approval record
            if request.user.labuser.is_principal_investigator:
                obj.last_changed_approval_by_pi = True
                if not obj.created_approval_by_pi: obj.created_approval_by_pi = True # Set created_approval_by_pi to True, should it still be None or False
                obj.approval_by_pi_date_time = timezone.now()

                if obj.approval.all().exists():
                    approval_records = obj.approval.all()
                    approval_records.delete()
            else:
                obj.last_changed_approval_by_pi = False

                # If an approval record for this object does not exist, create one
                if not obj.approval.all().exists():
                    obj.approval.create(activity_type='changed', activity_user=request.user)
                else:
                    # If an approval record for this object exists, check if a message was 
                    # sent. If so, update the approval record's edited field
                    approval_obj = obj.approval.all().latest('message_date_time')
                    if approval_obj.message_date_time:
                        if obj.last_changed_date_time > approval_obj.message_date_time:
                            approval_obj.edited = True
                            approval_obj.save()
            
            saved_obj = Oligo.objects.get(pk=obj.pk)
            if obj.info_sheet and obj.info_sheet != saved_obj.info_sheet:
                rename_doc = True
                obj.save_without_historical_record()
            else:
                obj.save()

            # else:
            #     raise PermissionDenied

        # Rename info_sheet
        if rename_doc:
            doc_dir_path = os.path.join(MEDIA_ROOT, 'collection/oligo/')
            old_file_name_abs_path = os.path.join(MEDIA_ROOT, obj.info_sheet.name)
            old_file_name, ext = os.path.splitext(os.path.basename(old_file_name_abs_path)) 
            new_file_name = os.path.join(
                'collection/oligo/',
                "o{}{}_{}_{}_{}{}".format(LAB_ABBREVIATION_FOR_FILES,
                                        obj.id,
                                        datetime.now().strftime("%Y%m%d"),
                                        datetime.now().strftime("%H%M%S"),
                                        datetime.now().strftime("%H%M%S"),
                                        ext.lower()))
            new_file_name_abs_path = os.path.join(MEDIA_ROOT, new_file_name)
            
            if not os.path.exists(doc_dir_path):
                os.makedirs(doc_dir_path) 
            
            os.rename(
                old_file_name_abs_path, 
                new_file_name_abs_path)

            obj.info_sheet.name = new_file_name
            obj.save()

            # For new records, delete first history record, which contains the unformatted info_sheet name, and change 
            # the newer history record's history_type from changed (~) to created (+). This gets rid of a duplicate
            # history record created when automatically generating a info_sheet name
            if new_obj:
                obj.history.last().delete()
                history_obj = obj.history.first()
                history_obj.history_type = "+"
                history_obj.save()

    def save_related(self, request, form, formsets, change):
        
        super(OligoPage, self).save_related(request, form, formsets, change)

        # Keep a record of the IDs of linked M2M fields in the main strain record
        # Not pretty, but it works

        obj = Oligo.objects.get(pk=form.instance.id)

        obj.history_formz_elements = list(obj.formz_elements.order_by('id').distinct('id').values_list('id', flat=True)) if obj.formz_elements.exists() else []
        obj.history_documents = list(obj.oligodoc_set.order_by('id').\
                                    distinct('id').values_list('id', flat=True)) \
                                    if obj.oligodoc_set.exists() else []

        obj.save_without_historical_record()

        history_obj = obj.history.latest()
        history_obj.history_formz_elements = obj.history_formz_elements
        history_obj.history_documents = obj.history_documents
        history_obj.save()

    def get_readonly_fields(self, request, obj=None):
        '''Override default get_readonly_fields to define user-specific read-only fields
        If a user is not a superuser, lab manager or the user who created a record
        return all fields as read-only 
        'created_date_time' and 'last_changed_date_time' fields must always be read-only
        because their set by Django itself'''
        
        if obj:
            if self.can_change:
                return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 
                        'last_changed_approval_by_pi','created_by'] 
            else:
                return ['name','sequence', 'us_e', 'gene', 'restriction_site', 'description', 
                        'comment', 'info_sheet', 'formz_elements', 'created_date_time',
                        'created_approval_by_pi', 'last_changed_date_time', 
                        'last_changed_approval_by_pi', 'created_by',]
        else:
            return ['created_date_time', 'created_approval_by_pi',
                    'last_changed_date_time', 'last_changed_approval_by_pi',]
    
    def add_view(self,request,extra_context=None):
        '''Override default add_view to show only desired fields'''
        
        self.fields = ('name','sequence', 'us_e', 'gene', 'restriction_site',
                       'description', 'comment', 'info_sheet',)
        return super(OligoPage,self).add_view(request)

    def change_view(self,request,object_id,extra_context=None):
        '''Override default change_view to show only desired fields'''

        self.can_change = False
        
        extra_context = extra_context or {}
        extra_context['show_disapprove'] = False

        if object_id:
            self.can_change = request.user == Oligo.objects.get(pk=object_id).created_by or \
                    request.user.groups.filter(name='Lab manager').exists() or \
                    request.user.is_superuser or request.user.labuser.is_principal_investigator
        
            if self.can_change:

                extra_context.update({'show_close': True,
                                 'show_save_and_add_another': True,
                                 'show_save_and_continue': True,
                                 'show_save_as_new': True,
                                 'show_save': True,})

            else:

                extra_context.update({'show_close': True,
                                 'show_save_and_add_another': True,
                                 'show_save_and_continue': True,
                                 'show_save_as_new': True,
                                 'show_save': True,})

            extra_context['show_disapprove'] = True if request.user.groups.filter(name='Approval manager').exists() else False

        if '_saveasnew' in request.POST:
            self.fields = ('name','sequence', 'us_e', 'gene', 'restriction_site',
                           'description', 'comment', 'info_sheet', 'formz_elements',)
            extra_context.update({'show_save_and_continue': False,
                        'show_save': False,
                        'show_save_and_add_another': False,
                        'show_disapprove': False,
                        'show_formz': False,
                        'show_obj_permission': False
                        })
        else:
            self.fields = ('name','sequence', 'us_e', 'gene', 'restriction_site', 'description',
                           'comment', 'info_sheet', 'formz_elements', 'created_date_time', 
                           'created_approval_by_pi', 'last_changed_date_time',
                           'last_changed_approval_by_pi', 'created_by',)

        return super(OligoPage,self).change_view(request,object_id, extra_context=extra_context)

    def response_change(self, request, obj):
        opts = self.model._meta
        preserved_filters = self.get_preserved_filters(request)

        msg_dict = {
            'name': opts.verbose_name,
            'obj': format_html('<a href="{}">{}</a>', urlquote(request.path), obj),
        }

        if "_disapprove_record" in request.POST:
            msg = format_html(
                _('The {name} "{obj}" was disapproved.'),
                **msg_dict)
            self.message_user(request, msg, messages.SUCCESS)
            return HttpResponseRedirect(reverse("admin:approval_recordtobeapproved_change", args=(obj.approval.latest('created_date_time').id,)))
        
        return super(OligoPage,self).response_change(request,obj)
    
    def get_history_array_fields(self):

        return {**super(OligoPage, self).get_history_array_fields(),
                'history_formz_elements': FormZBaseElement,
                'history_documents': OligoDoc
                }