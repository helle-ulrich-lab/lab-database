from django.contrib import admin
from django.http import HttpResponse
from django.utils.safestring import mark_safe
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
from django.contrib.admin.utils import quote
from django.template.response import TemplateResponse
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.core.mail import mail_admins
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponseNotFound
from django.core.serializers.json import Serializer as JsonSerializer
from django.urls import re_path

from djangoql.schema import DjangoQLSchema
from djangoql.admin import DjangoQLSearchMixin
from import_export import resources
from import_export.fields import Field
from djangoql.schema import StrField

import xlrd
import csv
import time
import json
from urllib.parse import quote as urlquote
import os
from uuid import uuid4
import urllib.parse
import re

from snapgene.pyclasses.client import Client
from snapgene.pyclasses.config import Config
import zmq

from common.shared_elements import SimpleHistoryWithSummaryAdmin
from common.shared_elements import AdminChangeFormWithNavigation
from common.shared_elements import SearchFieldOptUsername
from common.shared_elements import SearchFieldOptLastname

from .admin import FieldCreated
from .admin import FieldLastChanged
from .admin import FieldFormZProject
from .admin import FieldUse
from .admin import formz_as_html
from .admin import CustomGuardedModelAdmin
from .admin import Approval
from .admin import SortAutocompleteResultsId

from ..models.plasmid import Plasmid
from formz.models import FormZProject
from formz.models import FormZBaseElement
from formz.models import GenTechMethod

from django.conf import settings
BASE_DIR = settings.BASE_DIR
MEDIA_ROOT = settings.MEDIA_ROOT
LAB_ABBREVIATION_FOR_FILES = getattr(settings, 'LAB_ABBREVIATION_FOR_FILES', '')

from django.contrib.admin.options import IS_POPUP_VAR
from django.contrib.admin.options import TO_FIELD_VAR

from ..models.oligo import Oligo
from ..models.plasmid import Plasmid


class AdminOligosInPlasmid(admin.ModelAdmin):
    
    def get_urls(self):
        """
        Add navigation url
        """

        urls = super(AdminOligosInPlasmid, self).get_urls()

        urls = [re_path(r'^(?P<object_id>.+)/find_oligos/$', view=self.find_oligos)] + urls
        
        return urls

    def find_oligos(self, request, attempt_number=3, messages=[], *args, **kwargs):

        """ Given a path to a snapgene plasmid map, use snapegene server
        to detect common features and create map preview as png
        and gbk"""

        file_format = request.GET.get('file_format', 'gbk')

        if attempt_number > 0:
            try:
                # Connect to SnapGene server
                config = Config()
                server_ports = config.get_server_ports()
                for port in server_ports.values():
                    try:
                        client = Client(port, zmq.Context())
                    except:
                        continue
                    else:
                        break

                # Create paths for temp files
                temp_dir_path = os.path.join(BASE_DIR, "uploads/temp")
                oligos_json_path = os.path.join(temp_dir_path, str(uuid4()))
                dna_temp_path = os.path.join(temp_dir_path, str(uuid4()))
                gbk_temp_path = os.path.join(temp_dir_path, f'{str(uuid4())}.gb')

                # Write oligos to file
                if not Oligo.objects.exists():
                    return HttpResponseNotFound
                oligos = Oligo.objects.all().values_list('id', 'sequence')
                regexp = re.compile(r'[ATCGatcg].*$')
                oligos = list({"Name": f'! o{LAB_ABBREVIATION_FOR_FILES}{i[0]}',
                               "Sequence": i[1],
                               "Notes": "",} for i in filter(lambda x: regexp.search(x[1]), oligos))
                with open(oligos_json_path, 'w') as fhandle:
                    json.dump(oligos, fhandle)
                
                # Find oligos in plasmid map and convert result to gbk
                plasmid = self.model.objects.get(id=kwargs['object_id'])
                argument = {"request":"importPrimersFromList", "inputFile": plasmid.map.path, 
                            "inputPrimersFile": oligos_json_path, "outputFile": dna_temp_path}
                r = client.requestResponse(argument, 60000)
                r_code = r.get('code', 1)
                if r_code > 0:
                    error_message = 'importPrimersFromList - error ' + r_code
                    if error_message not in messages: messages.append(error_message)
                    client.close()
                    raise Exception
                
                # If user wants to download file, then do so
                if file_format == 'dna':
                    client.close()
                    # Get processed .dna map and delete temp files
                    with open(dna_temp_path, 'rb') as fhandle:
                        file_data = fhandle.read()

                    # os.unlink(oligos_json_path)
                    os.unlink(dna_temp_path)

                    # Send response
                    response = HttpResponse(file_data, content_type='application/octet-stream')
                    file_name = f"p{LAB_ABBREVIATION_FOR_FILES}{plasmid.id} - {plasmid.name} (imported oligos).dna"
                    response['Content-Disposition'] = f"attachment; filename*=utf-8''{urllib.parse.quote(file_name)}"
                    return response

                argument = {"request":"exportDNAFile", "inputFile": dna_temp_path,
                            "outputFile": gbk_temp_path, "exportFilter": "biosequence.gb"}
                r = client.requestResponse(argument, 10000)
                r_code = r.get('code', 1)
                if r_code > 0:
                    error_message = 'exportDNAFile - error ' + r_code
                    if error_message not in messages: messages.append(error_message)
                    client.close()
                    raise Exception

                client.close()

                # Get processed .gbk map and delete temp files
                with open(gbk_temp_path, 'r') as fhandle:
                    file_data = fhandle.read()

                os.unlink(oligos_json_path)
                os.unlink(dna_temp_path)
                os.unlink(gbk_temp_path)

                # Send response
                response = HttpResponse(file_data, content_type='text/plain')
                response['Content-Disposition'] = 'attachment; filename="map_with_imported_oligos.gbk"'
                return response
            
            except Exception as err:
                messages.append(str(err))
                self.find_oligos(request, attempt_number - 1, messages, *args, **kwargs)
        else:
            mail_admins("Error finding oligos in plasmid",
                        "There was an error with finding oligos in plasmid {} with snapgene server.\n\nErrors: {}.".format(kwargs['object_id'], str(messages)), 
                        fail_silently=True)
            raise Exception


class SearchFieldOptUsernamePlasmid(SearchFieldOptUsername):

    id_list = Plasmid.objects.all().values_list('created_by', flat=True).distinct()

class SearchFieldOptLastnamePlasmid(SearchFieldOptLastname):

    id_list = Plasmid.objects.all().values_list('created_by', flat=True).distinct()

class FieldFormZBaseElement(StrField):
    
    name = 'formz_elements_name'
    model = Plasmid
    suggest_options = True

    def get_options(self, search):
        
        if len(search) < 3:
            return ["Type 3 or more characters to see suggestions"]
        else:
            return FormZBaseElement.objects.filter(name__icontains=search).values_list('name', flat=True)

    def get_lookup_name(self):
        return 'formz_elements__name'

class PlasmidQLSchema(DjangoQLSchema):
    '''Customize search functionality'''
    
    include = (Plasmid, User) # Include only the relevant models to be searched

    def get_fields(self, model):
        '''Define fields that can be searched'''
        
        if model == Plasmid:
            return ['id', 'name', 'other_name', 'parent_vector', 'selection', FieldUse(), 'construction_feature', 'received_from', 'note', 
                'reference', 'created_by', FieldCreated(), FieldLastChanged(), FieldFormZBaseElement(), FieldFormZProject()]
        elif model == User:
            return [SearchFieldOptUsernamePlasmid(), SearchFieldOptLastnamePlasmid()]
        return super(PlasmidQLSchema, self).get_fields(model)

class PlasmidExportResource(resources.ModelResource):
    """Defines a custom export resource class for Plasmid"""
    
    additional_parent_vector_info = Field(attribute='old_parent_vector', column_name='additional_parent_vector_info')

    class Meta:
        model = Plasmid
        fields = ('id', 'name', 'other_name', 'parent_vector', 'additional_parent_vector_info', 'selection', 'us_e', 
                  'construction_feature', 'received_from', 'note', 'reference', 'map', 'created_date_time',
                  'created_by__username',)
        export_order = ('id', 'name', 'other_name', 'parent_vector', 'additional_parent_vector_info', 'selection', 'us_e', 
                  'construction_feature', 'received_from', 'note', 'reference', 'map', 'created_date_time',
                  'created_by__username',)

def export_plasmid(modeladmin, request, queryset):
    """Export Plasmid"""

    export_data = PlasmidExportResource().export(queryset)

    file_format = request.POST.get('format', default='xlsx')

    if file_format == 'xlsx':
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="{}_{}_{}.xlsx'.format(queryset.model.__name__, time.strftime("%Y%m%d"), time.strftime("%H%M%S"))
        response.write(export_data.xlsx)
    elif file_format == 'tsv':
        response = HttpResponse(content_type='text/tab-separated-values')
        response['Content-Disposition'] = 'attachment; filename="{}_{}_{}.tsv'.format(queryset.model.__name__, time.strftime("%Y%m%d"), time.strftime("%H%M%S"))
        xlsx_file = xlrd.open_workbook(file_contents=export_data.xlsx)
        sheet = xlsx_file.sheet_by_index(0)
        wr = csv.writer(response, delimiter="\t")
        for rownum in range(sheet.nrows):
            row_values = [str(i).replace("\n", "").replace('\r', '').replace("\t", "") for i in sheet.row_values(rownum)]
            wr.writerow(row_values)
    return response
export_plasmid.short_description = "Export selected plasmids"

class PlasmidForm(forms.ModelForm):
    
    class Meta:
        model = Plasmid
        fields = '__all__'

    def clean_name(self):
        """Check if name is unique before saving"""
        
        if not self.instance.pk:
            if Plasmid.objects.filter(name=self.cleaned_data["name"]).exists():
                raise forms.ValidationError('Plasmid with this name already exists.')
            else:
                return self.cleaned_data["name"]
        else:
            if Plasmid.objects.filter(name=self.cleaned_data["name"]).exclude(id=self.instance.pk).exists():
                raise forms.ValidationError('Plasmid with this name already exists.')
            else:
                return self.cleaned_data["name"]

    def clean(self):

        """Check if both the .dna and .gbk map is changed at the same time, which 
        is not allowed"""

        map_dna = self.cleaned_data.get('map', None)
        map_gbk = self.cleaned_data.get('map_gbk', None)

        if not self.instance.pk:
            if map_dna and map_gbk:
                self.add_error(None, "You cannot add both a .dna and a .gbk map at the same time. Please choose only one")

        else:
            saved_obj = Plasmid.objects.get(id=self.instance.pk)
            saved_dna_map = saved_obj.map.name if saved_obj.map.name else None
            saved_gbk_map = saved_obj.map_gbk.name if saved_obj.map_gbk.name else None

            if  map_dna != saved_dna_map and map_gbk != saved_gbk_map:
                self.add_error(None, "You cannot change both a .dna and a .gbk map at the same time. Please choose only one")

        return self.cleaned_data

class PlasmidPage(DjangoQLSearchMixin, SimpleHistoryWithSummaryAdmin, CustomGuardedModelAdmin, Approval, AdminChangeFormWithNavigation, AdminOligosInPlasmid, SortAutocompleteResultsId):
    
    list_display = ('id', 'name', 'selection', 'get_plasmidmap_short_name', 'created_by', 'approval')
    list_display_links = ('id',)
    list_per_page = 25
    formfield_overrides = {CharField: {'widget': TextInput(attrs={'size':'93'})},} # Make TextInput fields wider
    djangoql_schema = PlasmidQLSchema
    djangoql_completion_enabled_by_default = False
    actions = [export_plasmid, formz_as_html]
    search_fields = ['id', 'name']
    autocomplete_fields = ['parent_vector', 'formz_projects', 'formz_elements', 'vector_zkbs', 'formz_ecoli_strains', 'formz_gentech_methods']
    redirect_to_obj_page = False
    form = PlasmidForm

    change_form_template = "admin/collection/plasmid/change_form.html"
    add_form_template = "admin/collection/plasmid/change_form.html"

    def save_model(self, request, obj, form, change):
        '''Override default save_model to limit a user's ability to save a record
        Superusers and lab managers can change all records
        Regular users can change only their own records
        Guests cannot change any record.
        It also renames a plasmid map to pNZ{obj.id}_{date_created}_{time_created}.ext
        and whenever possible creates a plasmid map preview with snapegene server'''
        
        rename_and_preview = False
        self.rename_and_preview = False
        new_obj = False
        self.new_obj = False
        self.clear_formz_elements = False
        convert_map_to_dna = False

        if obj.pk == None:

            obj.id = Plasmid.objects.order_by('-id').first().id + 1 if Plasmid.objects.exists() else 1
            obj.created_by = request.user
            obj.save()
            new_obj = True
            self.new_obj = True

            # If a plasmid is 'Saved as new', clear all form Z elements
            if "_saveasnew" in request.POST and (obj.map or obj.map_gbk):
                self.clear_formz_elements = True
            
            # Check if a map is present and if so trigger functions to create a plasmid
            # map preview and delete the resulting duplicate history record
            if obj.map:
                rename_and_preview = True
                self.rename_and_preview = True
            elif obj.map_gbk:
                rename_and_preview = True
                self.rename_and_preview = True
                convert_map_to_dna = True

            # If the request's user is the principal investigator, approve the record
            # right away. If not, create an approval record
            if request.user.labuser.is_principal_investigator and request.user.id in obj.formz_projects.all().values_list('project_leader__id', flat=True):
                original_last_changed_date_time = obj.last_changed_date_time
                obj.created_approval_by_pi = True
                obj.approval_user = request.user
                obj.approval_by_pi_date_time = timezone.now()
                obj.save_without_historical_record()
                Plasmid.objects.filter(id=obj.pk).update(last_changed_date_time=original_last_changed_date_time)
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
                    obj.approval_user = None
                    obj.save_without_historical_record()
                    Plasmid.objects.filter(id=obj.pk).update(last_changed_date_time=original_last_changed_date_time)
                return

            # Approve right away if the request's user is the principal investigator. If not,
            # create an approval record
            if request.user.labuser.is_principal_investigator and request.user.id in obj.formz_projects.all().values_list('project_leader__id', flat=True):
                obj.last_changed_approval_by_pi = True
                if not obj.created_approval_by_pi: obj.created_approval_by_pi = True # Set created_approval_by_pi to True, should it still be None or False
                obj.approval_user = request.user
                obj.approval_by_pi_date_time = timezone.now()
                if obj.approval.all().exists():
                    approval_records = obj.approval.all()
                    approval_records.delete()
 
            else:
                obj.last_changed_approval_by_pi = False
                obj.approval_user = None

                # If an approval record for this object does not exist, create one
                if not obj.approval.all().exists():
                    obj.approval.create(activity_type='changed', activity_user=request.user)
                else:
                    # If an approval record for this object exists, check if a message was 
                    # sent. If so, update the approval record's edited field
                    approval_obj = obj.approval.all().latest('message_date_time')
                    if approval_obj.message_date_time:
                        if timezone.now() > approval_obj.message_date_time:
                            approval_obj.edited = True
                            approval_obj.save()

            # Check if the request's user can change the object, if not raise PermissionDenied

            saved_obj = Plasmid.objects.get(pk=obj.pk)

            if self.can_change:

                if obj.map != saved_obj.map or obj.map_gbk != saved_obj.map_gbk:

                    if (obj.map and obj.map_gbk) or (not saved_obj.map and not saved_obj.map_gbk): 
                        rename_and_preview = True
                        self.rename_and_preview = True
                        obj.save_without_historical_record()
                        
                        if obj.map_gbk != saved_obj.map_gbk:
                            convert_map_to_dna = True

                    else:
                        obj.map.name = ''
                        obj.map_png.name = ''
                        obj.map_gbk.name = ''
                        self.clear_formz_elements = True
                        obj.save()
                
                else:
                    obj.save()

            else:
                
                if obj.created_by.labuser.is_principal_investigator: # Allow saving object, if record belongs to principal investigator
                    
                    if obj.map != saved_obj.map or obj.map_gbk != saved_obj.map_gbk:

                        if (obj.map and obj.map_gbk) or (not saved_obj.map and not saved_obj.map_gbk): 
                            rename_and_preview = True
                            self.rename_and_preview = True
                            obj.save_without_historical_record()
                            
                            if obj.map_gbk != saved_obj.map_gbk:
                                convert_map_to_dna = True

                        else:
                            obj.map.name = ''
                            obj.map_png.name = ''
                            obj.map_gbk.name = ''
                            self.clear_formz_elements = True
                            obj.save()
                    
                    else:
                        obj.save()

                else:
                    raise PermissionDenied
        
        # Rename plasmid map
        if rename_and_preview:

            new_file_name = "p{}{}_{}_{}".format(LAB_ABBREVIATION_FOR_FILES, obj.id, time.strftime("%Y%m%d"), time.strftime("%H%M%S"))
            
            new_dna_file_name = os.path.join('collection/plasmid/dna/', new_file_name + '.dna')
            new_gbk_file_name = os.path.join('collection/plasmid/gbk/', new_file_name + '.gbk')
            new_png_file_name = os.path.join('collection/plasmid/png/', new_file_name + '.png')
            
            new_dna_file_path = os.path.join(MEDIA_ROOT, new_dna_file_name)
            new_gbk_file_path = os.path.join(MEDIA_ROOT, new_gbk_file_name)

            if convert_map_to_dna:
                old_gbk_file_path = obj.map_gbk.path
                os.rename(
                    old_gbk_file_path, 
                    new_gbk_file_path)
                try:
                    self.convert_plasmid_map_gbk_to_dna(new_gbk_file_path, new_dna_file_path)
                except:
                    messages.error(request, 'There was an error with converting your plasmid map to .gbk.')
            else:
                old_dna_file_path = obj.map.path
                os.rename(
                    old_dna_file_path, 
                    new_dna_file_path)
            
            obj.map.name = new_dna_file_name
            obj.map_png.name = new_png_file_name 
            obj.map_gbk.name = new_gbk_file_name
            obj.save()

            # For new records, delete first history record, which contains the unformatted map name, and change 
            # the newer history record's history_type from changed (~) to created (+). This gets rid of a duplicate
            # history record created when automatically generating a map name
            if new_obj:
                obj.history.last().delete()
                history_obj = obj.history.first()
                history_obj.history_type = "+"
                history_obj.save()
            
            # For plasmid map, detect common features and save as png using snapgene server
            try:
                detect_common_features_map_dna = request.POST.get("detect_common_features_map", False)
                detect_common_features_map_gbk = request.POST.get("detect_common_features_map_gbk", False)
                detect_common_features = True if (detect_common_features_map_dna or detect_common_features_map_gbk) else False
                self.create_plasmid_map_preview(obj.map.path, obj.map_png.path, obj.map_gbk.path, obj.id, obj.name, detect_common_features)
            except:
                messages.error(request, 'There was an error with detection of common features and/or saving of the map preview')


    def save_related(self, request, form, formsets, change):
        
        super(PlasmidPage, self).save_related(request, form, formsets, change)

        obj = Plasmid.objects.get(pk=form.instance.id)

        # If a plasmid map is provided, automatically add those
        # for which a corresponding FormZ base element is present
        # in the database

        if self.clear_formz_elements:
            obj.formz_elements.clear()

        if self.rename_and_preview or "_redetect_formz_elements" in request.POST:
            
            unknown_feat_name_list = []
            
            try:
                feature_names = self.get_plasmid_map_features(obj.map.path)
            except:
                messages.error(request, 'There was an error getting your plasmid map features')
                feature_names = []
            
            if not self.new_obj:
                obj.formz_elements.clear()
            
            if feature_names:
            
                formz_base_elems = FormZBaseElement.objects.filter(extra_label__label__in = feature_names).distinct()
                aliases = list(formz_base_elems.values_list('extra_label__label', flat=True))
                obj.formz_elements.add(*list(formz_base_elems))

                unknown_feat_name_list = [feat for feat in feature_names if feat not in aliases]

                if unknown_feat_name_list:
                    self.redirect_to_obj_page = True
                    unknown_feat_name_list = str(unknown_feat_name_list)[1:-1].replace("'", "")
                    messages.warning(request, mark_safe("The following plasmid features were not added to <span style='background-color:rgba(0,0,0,0.1);'>FormZ Elements</span>,"
                                        " because they cannot be found in the database: <span class='missing-formz-features' style='background-color:rgba(255,0,0,0.2)'>{}</span>. You may want to add them manually "
                                        "yourself below.".format(unknown_feat_name_list)))
            else:
                self.redirect_to_obj_page = False

        # Keep a record of the IDs of linked M2M fields in the main strain record
        # Not pretty, but it works

        obj.history_formz_projects = list(obj.formz_projects.order_by('id').distinct('id').values_list('id', flat=True)) if obj.formz_projects.exists() else []
        obj.history_formz_elements = list(obj.formz_elements.order_by('id').distinct('id').values_list('id', flat=True)) if obj.formz_elements.exists() else []
        obj.history_formz_ecoli_strains = list(obj.formz_ecoli_strains.order_by('id').distinct('id').values_list('id', flat=True)) if obj.formz_ecoli_strains.exists() else []
        obj.history_formz_gentech_methods = list(obj.formz_gentech_methods.order_by('id').distinct('id').values_list('id', flat=True)) if obj.formz_gentech_methods.exists() else []

        # For new records without map preview, delete first history record, which contains the unformatted map name, and change 
        # the newer history record's history_type from changed (~) to created (+). This gets rid of a duplicate
        # history record created when automatically generating a map name
        if self.new_obj and not self.rename_and_preview:
            obj.save()
            obj.history.last().delete()
            history_obj = obj.history.first()
            history_obj.history_type = "+"
            history_obj.save()
        else:
            obj.save_without_historical_record()

        history_obj = obj.history.latest()
        history_obj.history_formz_projects = obj.history_formz_projects
        history_obj.history_formz_elements = obj.history_formz_elements
        history_obj.history_formz_ecoli_strains = obj.history_formz_ecoli_strains
        history_obj.history_formz_gentech_methods = obj.history_formz_gentech_methods
        history_obj.save()

    def response_add(self, request, obj, post_url_continue=None):
        """
        Determine the HttpResponse for the add_view stage.
        """

        opts = obj._meta
        preserved_filters = self.get_preserved_filters(request)
        obj_url = reverse(
            'admin:%s_%s_change' % (opts.app_label, opts.model_name),
            args=(quote(obj.pk),),
            current_app=self.admin_site.name,
        )
        # Add a link to the object's change form if the user can edit the obj.
        if self.has_change_permission(request, obj):
            obj_repr = format_html('<a href="{}">{}</a>', urlquote(obj_url), obj)
        else:
            obj_repr = str(obj)
        msg_dict = {
            'name': opts.verbose_name,
            'obj': obj_repr,
        }
        # Here, we distinguish between different save types by checking for
        # the presence of keys in request.POST.

        if IS_POPUP_VAR in request.POST:
            to_field = request.POST.get(TO_FIELD_VAR)
            if to_field:
                attr = str(to_field)
            else:
                attr = obj._meta.pk.attname
            value = obj.serializable_value(attr)
            popup_response_data = json.dumps({
                'value': str(value),
                'obj': str(obj),
            })
            return TemplateResponse(request, self.popup_response_template or [
                'admin/%s/%s/popup_response.html' % (opts.app_label, opts.model_name),
                'admin/%s/popup_response.html' % opts.app_label,
                'admin/popup_response.html',
            ], {
                'popup_response_data': popup_response_data,
            })

        elif "_continue" in request.POST or (
                # Redirecting after "Save as new".
                "_saveasnew" in request.POST and self.save_as_continue and
                self.has_change_permission(request, obj)
        ) or self.redirect_to_obj_page: # Check if obj has unidentified FormZ Elements
            msg = _('The {name} "{obj}" was added successfully.')
            if self.has_change_permission(request, obj):
                msg += ' ' + _('You may edit it again below.')
            self.message_user(request, format_html(msg, **msg_dict), messages.SUCCESS)
            if post_url_continue is None:
                post_url_continue = obj_url
            post_url_continue = add_preserved_filters(
                {'preserved_filters': preserved_filters, 'opts': opts},
                post_url_continue
            )
            return HttpResponseRedirect(post_url_continue)

        elif "_addanother" in request.POST:
            msg = format_html(
                _('The {name} "{obj}" was added successfully. You may add another {name} below.'),
                **msg_dict
            )
            self.message_user(request, msg, messages.SUCCESS)
            redirect_url = request.path
            redirect_url = add_preserved_filters({'preserved_filters': preserved_filters, 'opts': opts}, redirect_url)
            return HttpResponseRedirect(redirect_url)

        else:
            msg = format_html(
                _('The {name} "{obj}" was added successfully.'),
                **msg_dict
            )
            self.message_user(request, msg, messages.SUCCESS)
            return self.response_post_save_add(request, obj)

    def response_change(self, request, obj):
        """
        Determine the HttpResponse for the change_view stage.
        """

        if IS_POPUP_VAR in request.POST:
            opts = obj._meta
            to_field = request.POST.get(TO_FIELD_VAR)
            attr = str(to_field) if to_field else opts.pk.attname
            value = request.resolver_match.kwargs['object_id']
            new_value = obj.serializable_value(attr)
            popup_response_data = json.dumps({
                'action': 'change',
                'value': str(value),
                'obj': str(obj),
                'new_value': str(new_value),
            })
            return TemplateResponse(request, self.popup_response_template or [
                'admin/%s/%s/popup_response.html' % (opts.app_label, opts.model_name),
                'admin/%s/popup_response.html' % opts.app_label,
                'admin/popup_response.html',
            ], {
                'popup_response_data': popup_response_data,
            })

        opts = self.model._meta
        preserved_filters = self.get_preserved_filters(request)

        msg_dict = {
            'name': opts.verbose_name,
            'obj': format_html('<a href="{}">{}</a>', urlquote(request.path), obj),
        }

        if "_disapprove_record" in request.POST:
            msg = format_html(
                _('The {name} "{obj}" was disapproved.'),
                **msg_dict
            )
            self.message_user(request, msg, messages.SUCCESS)
            return HttpResponseRedirect(reverse("admin:approval_recordtobeapproved_change", args=(obj.approval.latest('created_date_time').id,)))

        if "_continue" in request.POST or self.redirect_to_obj_page: # Check if obj has unidentified FormZ Elements:
            msg = format_html(
                _('The {name} "{obj}" was changed successfully. You may edit it again below.'),
                **msg_dict
            )
            self.message_user(request, msg, messages.SUCCESS)
            redirect_url = request.path
            redirect_url = add_preserved_filters({'preserved_filters': preserved_filters, 'opts': opts}, redirect_url)
            return HttpResponseRedirect(redirect_url)

        elif "_saveasnew" in request.POST:
            msg = format_html(
                _('The {name} "{obj}" was added successfully. You may edit it again below.'),
                **msg_dict
            )
            self.message_user(request, msg, messages.SUCCESS)
            redirect_url = reverse('admin:%s_%s_change' %
                                   (opts.app_label, opts.model_name),
                                   args=(obj.pk,),
                                   current_app=self.admin_site.name)
            redirect_url = add_preserved_filters({'preserved_filters': preserved_filters, 'opts': opts}, redirect_url)
            return HttpResponseRedirect(redirect_url)

        elif "_addanother" in request.POST:
            msg = format_html(
                _('The {name} "{obj}" was changed successfully. You may add another {name} below.'),
                **msg_dict
            )
            self.message_user(request, msg, messages.SUCCESS)
            redirect_url = reverse('admin:%s_%s_add' %
                                   (opts.app_label, opts.model_name),
                                   current_app=self.admin_site.name)
            redirect_url = add_preserved_filters({'preserved_filters': preserved_filters, 'opts': opts}, redirect_url)
            return HttpResponseRedirect(redirect_url)

        else:
            msg = format_html(
                _('The {name} "{obj}" was changed successfully.'),
                **msg_dict
            )
            self.message_user(request, msg, messages.SUCCESS)
            return self.response_post_save_change(request, obj)

    def get_readonly_fields(self, request, obj=None):
        '''Override default get_readonly_fields to define user-specific read-only fields
        If a user is not a superuser, lab manager or the user who created a record
        return all fields as read-only
        'created_date_time' and 'last_changed_date_time' fields must always be read-only
        because their set by Django itself'''
        
        if obj:
            if request.user.has_perm('collection.change_plasmid', obj):
                return ['map_png', 'created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by',]
            if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by or obj.created_by.labuser.is_principal_investigator or obj.created_by.groups.filter(name='Past member').exists()):
                return ['name', 'other_name', 'parent_vector', 'old_parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 'note', 
                    'reference', 'map', 'map_png', 'map_gbk', 'created_date_time', 'created_approval_by_pi', 'last_changed_date_time',
                    'last_changed_approval_by_pi', 'created_by', 'formz_projects', 'formz_risk_group', 'vector_zkbs', 
                    'destroyed_date', 'formz_elements', 'formz_gentech_methods', 'formz_ecoli_strains']
            else:
                if (obj.created_by.labuser.is_principal_investigator or obj.created_by.groups.filter(name='Past member').exists()) and not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists()): # Show map and note as editable fields, if record belongs to PI or old member
                    return ['name', 'other_name', 'parent_vector', 'old_parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 
                    'reference', 'map_png', 'created_date_time', 'created_approval_by_pi', 'last_changed_date_time',
                    'last_changed_approval_by_pi', 'created_by', 'formz_projects', 'formz_risk_group', 'vector_zkbs', 
                    'destroyed_date', 'formz_elements', 'formz_gentech_methods', 'formz_ecoli_strains']
                else:
                    return ['map_png', 'created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi','created_by',]
        else:
            return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi',]
    
    def add_view(self, request, extra_context=None):
        '''Override default add_view to show only desired fields'''

        self.fieldsets = (
        (None, {
            'fields': ('name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 'note', 
                'reference', 'map', 'map_gbk')
        }),
        ('FormZ', {
            'fields': ('formz_projects', 'formz_risk_group', 'vector_zkbs', 'formz_gentech_methods', 'formz_elements', 'formz_ecoli_strains', 'destroyed_date',)
        }),
        )
        
        return super(PlasmidPage,self).add_view(request)
    
    def change_view(self, request, object_id, extra_context=None):
        '''Override default change_view to show only desired fields'''

        self.can_change = False

        extra_context = extra_context or {}
        extra_context['show_disapprove'] = False
        extra_context['show_formz'] = False

        if object_id:
            
            obj = Plasmid.objects.get(pk=object_id)
            
            if request.user == obj.created_by or request.user.groups.filter(name='Lab manager').exists() or \
                request.user.labuser.is_principal_investigator or request.user.is_superuser or \
                obj.created_by.labuser.is_principal_investigator or obj.created_by.groups.filter(name='Past member') or \
                request.user.has_perm('collection.change_plasmid', obj):
                    
                    self.can_change = True
                    
                    if (obj.created_by.labuser.is_principal_investigator or obj.created_by.groups.filter(name='Past member')) and \
                        not request.user.has_perm('collection.change_plasmid', obj):
                        
                        extra_context.update({'show_close': True,
                                        'show_save_and_add_another': False,
                                        'show_save_and_continue': True,
                                        'show_save_as_new': False,
                                        'show_save': True,
                                        'show_obj_permission': False,
                                        'show_redetect_save': True})
                    else:

                        extra_context.update({'show_close': True,
                                    'show_save_and_add_another': True,
                                    'show_save_and_continue': True,
                                    'show_save_as_new': True,
                                    'show_save': True,
                                    'show_obj_permission': True,
                                    'show_redetect_save': True})

            else:
                
                extra_context.update({'show_close': True,
                                 'show_save_and_add_another': False,
                                 'show_save_and_continue': False,
                                 'show_save_as_new': False,
                                 'show_save': False,
                                 'show_obj_permission': False,
                                 'show_redetect_save': False})
            
            extra_context['show_disapprove'] = True if request.user.groups.filter(name='Approval manager').exists() else False
            extra_context['show_formz'] = True

        fieldsets_with_keep = (
                (None, {
                    'fields': ('name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 'note', 
                        'reference', 'map', 'map_png', 'map_gbk', 'created_date_time', 'created_approval_by_pi', 'last_changed_date_time',
                        'last_changed_approval_by_pi', 'created_by', )
                }),
                ('FormZ', {
                    'classes': ('collapse',) if not request.GET.get('_approval', '') else tuple(),
                    'fields': ('formz_projects', 'formz_risk_group', 'vector_zkbs', 'formz_gentech_methods', 'formz_elements', 'formz_ecoli_strains', 'destroyed_date',)
                }),
                )

        fieldsets_wo_keep = (
                (None, {
                    'fields': ('name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 'note', 
                        'reference', 'map', 'map_png', 'map_gbk', 'created_date_time', 'created_approval_by_pi', 'last_changed_date_time',
                        'last_changed_approval_by_pi', 'created_by', )
                }),
                ('FormZ', {
                    'classes': ('collapse',) if not request.GET.get('_approval', '') else tuple(),
                    'fields': ('formz_projects', 'formz_risk_group', 'vector_zkbs', 'formz_gentech_methods', 'formz_elements', 'formz_ecoli_strains', 'destroyed_date',)
                }),
                )

        if '_saveasnew' in request.POST:
            self.fieldsets = (
                (None, {
                    'fields': ('name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 'note', 
                'reference', 'map', 'map_gbk',)
                }),
                ('FormZ', {
                    'fields': ('formz_projects', 'formz_risk_group', 'vector_zkbs', 'formz_gentech_methods', 'formz_elements', 'formz_ecoli_strains', 'destroyed_date',)
                    }),
                )
            
            extra_context.update({'show_save_and_continue': False,
                                 'show_save': False,
                                 'show_save_and_add_another': False,
                                 'show_disapprove': False,
                                 'show_formz': False,
                                 'show_redetect_save': False,
                                 'show_obj_permission': False
                                 })

        else:
            if request.user.has_perm('collection.change_plasmid', obj):
                self.fieldsets = fieldsets_with_keep
            if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by or obj.created_by.labuser.is_principal_investigator):
                self.fieldsets = fieldsets_wo_keep
            else:
                if obj.created_by.labuser.is_principal_investigator and not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists()):
                    self.fieldsets = fieldsets_with_keep
                else:
                    self.fieldsets = fieldsets_wo_keep
        
        return super(PlasmidPage, self).change_view(request, object_id, extra_context=extra_context)

    def get_plasmidmap_short_name(self, instance):
        '''This function allows you to define a custom field for the list view to
        be defined in list_display as the name of the function, e.g. in this case
        list_display = ('id', 'name', 'selection', 'get_plasmidmap_short_name','created_by',)'''
        
        if instance.map:
            ove_dna_preview = instance.get_ove_url_map()
            ove_gbk_preview =  instance.get_ove_url_map_gbk()
            return mark_safe(f'<a class="magnific-popup-img-plasmidmap" href="{instance.map_png.url}">png</a> | '
                             f'<a href="{instance.map.url}">dna</a> <a class="magnific-popup-iframe-plasmidmap-dna" href="{ove_dna_preview}">⊙</a> | '
                             f'<a href="{instance.map_gbk.url}">gbk</a> <a class="magnific-popup-iframe-plasmidmap-gbk" href="{ove_gbk_preview}">⊙</a>')
        else:
            return ''
    get_plasmidmap_short_name.short_description = 'Plasmid map'

    def obj_perms_manage_view(self, request, object_pk):
        """
        Main object Guardian permissions view. 

        Customized to allow only record owner to change permissions
        """
        obj = Plasmid.objects.get(pk=object_pk)
        
        if obj:
            if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or \
                request.user == obj.created_by or request.user.labuser.is_principal_investigator):
                messages.error(request, 'Nice try, you are allowed to change the permissions of your own records only.')
                return HttpResponseRedirect("..")
        return super(PlasmidPage,self).obj_perms_manage_view(request, object_pk)

    #@background(schedule=1) # Run 1 s after it is called, as "background" process
    def create_plasmid_map_preview(self, plasmid_map_path, png_plasmid_map_path, gbk_plasmid_map_path, obj_id, obj_name, detect_common_features, attempt_number=3, messages=[]):
        """ Given a path to a snapgene plasmid map, use snapegene server
        to detect common features and create map preview as png
        and gbk"""

        if attempt_number > 0:
            try:
                config = Config()
                server_ports = config.get_server_ports()
                for port in server_ports.values():
                    try:
                        client = Client(port, zmq.Context())
                    except:
                        continue
                    else:
                        break
                
                common_features_path = os.path.join(BASE_DIR, "snapgene/standardCommonFeatures.ftrs")
                
                if detect_common_features:
                    argument = {"request":"detectFeatures", "inputFile": plasmid_map_path, 
                    "outputFile": plasmid_map_path, "featureDatabase": common_features_path}
                    r = client.requestResponse(argument, 10000)
                    r_code = r.get('code', 1)
                    if r_code > 0:
                        error_message = 'detectFeatures - error ' + r_code
                        if error_message not in messages: messages.append(error_message)
                        client.close()
                        raise Exception
                
                argument = {"request":"generatePNGMap", "inputFile": plasmid_map_path,
                "outputPng": png_plasmid_map_path, "title": "p{}{} - {}".format(LAB_ABBREVIATION_FOR_FILES, obj_id, obj_name),
                "showEnzymes": True, "showFeatures": True, "showPrimers": True, "showORFs": False}
                r = client.requestResponse(argument, 10000)
                r_code = r.get('code', 1)
                if r_code > 0:
                    error_message = 'generatePNGMap - error ' + r_code
                    if error_message not in messages: messages.append(error_message)
                    client.close()
                    raise Exception
                
                argument = {"request":"exportDNAFile", "inputFile": plasmid_map_path,
                "outputFile": gbk_plasmid_map_path, "exportFilter": "biosequence.gb"}
                r = client.requestResponse(argument, 10000)
                r_code = r.get('code', 1)
                if r_code > 0:
                    error_message = 'exportDNAFile - error ' + r_code
                    if error_message not in messages: messages.append(error_message)
                    client.close()
                    raise Exception

                client.close()

            except:
                self.create_plasmid_map_preview(plasmid_map_path, png_plasmid_map_path, gbk_plasmid_map_path, obj_id, obj_name, detect_common_features, attempt_number - 1, messages)

        else:
            mail_admins("Snapgene server error", 
                        "There was an error with creating the preview for {} with snapgene server.\n\nErrors: {}.".format(plasmid_map_path, str(messages)), 
                        fail_silently=True)
            raise Exception

    def get_plasmid_map_features(self, plasmid_map_path, attempt_number=3, messages=[]):
        """ Given a path to a snapgene plasmid map (.dna), use snapegene server
        to return features, as json"""

        if attempt_number > 0:
            try:
                config = Config()
                server_ports = config.get_server_ports()
                for port in server_ports.values():
                    try:
                        client = Client(port, zmq.Context())
                    except:
                        continue
                    else:
                        break
            
                argument = {"request":"reportFeatures", "inputFile": plasmid_map_path}
                r = client.requestResponse(argument, 10000)
                r_code = r.get('code', 1)
                if r_code > 0:
                    error_message = 'reportFeatures - error ' + r_code
                    if error_message not in messages: messages.append(error_message)
                    client.close()
                    raise Exception
                
                client.close()
                
                plasmid_features = r.get('features', [])
                feature_names = [feat['name'].strip() for feat in plasmid_features]
                return feature_names
            
            except:
                self.get_plasmid_map_features(plasmid_map_path, attempt_number - 1, messages)
        
        else:
            mail_admins("Snapgene server error", 
                        "There was an error with getting plasmid features for {} with snapgene server.\n\nErrors: {}.".format(plasmid_map_path, str(messages)), 
                        fail_silently=True)
            raise Exception

    def convert_plasmid_map_gbk_to_dna(self, gbk_map_path, dna_map_path, attempt_number=3, messages=[]):
        """ Given a path to a snapgene plasmid map (.dna), use snapegene server
        to return features, as json"""

        if attempt_number > 0:
            try:
                config = Config()
                server_ports = config.get_server_ports()
                for port in server_ports.values():
                    try:
                        client = Client(port, zmq.Context())
                    except:
                        continue
                    else:
                        break
                
                argument = {"request":"importDNAFile", "inputFile": gbk_map_path, 'outputFile': dna_map_path}
                r = client.requestResponse(argument, 10000)
                r_code = r.get('code', 1)
                if r_code > 0:
                    error_message = 'importDNAFile - error ' + r_code
                    if error_message not in messages: messages.append(error_message)
                    client.close()
                    raise Exception

                client.close()
            
            except:
                self.convert_plasmid_map_gbk_to_dna(gbk_map_path, dna_map_path, attempt_number - 1, messages)
        
        else:
            mail_admins("Snapgene server error", 
                        "There was an error converting a gbk map to dna for {} with snapgene server.\n\nErrors: {}.".format(gbk_map_path, str(messages)), 
                        fail_silently=True)
            raise Exception

    def get_history_array_fields(self):

        return {**super(PlasmidPage, self).get_history_array_fields(),
                'history_formz_projects': FormZProject,
                'history_formz_gentech_methods': GenTechMethod,
                'history_formz_elements': FormZBaseElement,
                'history_formz_ecoli_strains': FormZBaseElement,
                }
