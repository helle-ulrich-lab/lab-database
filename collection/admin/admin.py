from django.contrib import admin
from django.contrib import messages
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponseRedirect
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render
from django.urls import re_path

from djangoql.schema import StrField
from djangoql.schema import IntField
from djangoql.schema import DateTimeField
from background_task import background
from guardian.admin import GuardedModelAdmin
from guardian.admin import UserManage

import time
from formz.models import FormZProject

#################################################
#                CUSTOM CLASSES                 #
#################################################

class Approval():
    def approval(self, instance):

        """ Custom list_view field to show whether record has been approved or not """

        if instance.last_changed_approval_by_pi is not None:
            return instance.last_changed_approval_by_pi
        else:
            return instance.created_approval_by_pi
    approval.boolean = True
    approval.short_description = "Approved"

class CustomUserManage(UserManage):
    
    """
    Add drop-down menu to select user to who to give additonal permissions
    """

    from django import forms

    try: # Added this try block because if user_auth table not present in DB (e.g. very first migration) the following code runs and throws an exception
        user = forms.ChoiceField(choices=[('------', '------')] + [(u.username, u) for u in User.objects.all().order_by('last_name') if u.groups.filter(name='Regular lab member').exists()],
                                label=_("Username"),
                            error_messages={'does_not_exist': _(
                                "This user does not exist")},)
        is_permanent = forms.BooleanField(required=False, label=_("Grant indefinitely?"))
    except:
        pass

class SortAutocompleteResultsId(admin.ModelAdmin):

    def get_ordering(self, request):
        # Force sorting of autocompletion results to be by ascending id
        if request.path_info == '/autocomplete/':
            return ['id']
        else:
            return super(SortAutocompleteResultsId, self).get_ordering(request)

@background(schedule=86400) # Run 24 h after it is called, as "background" process
def delete_obj_perm_after_24h(perm, user_id, obj_id, app_label, model_name):
    """ Delete object permession after 24 h"""
    
    from django.apps import apps
    from guardian.shortcuts import remove_perm
    
    user = User.objects.get(id=user_id)
    obj = apps.get_model(app_label, model_name).objects.get(id=obj_id)

    remove_perm(perm, user, obj)

class CustomGuardedModelAdmin(GuardedModelAdmin):

    def get_urls(self):
        """
        Extends standard guardian admin model urls with delete url
        """
        
        urls = super(CustomGuardedModelAdmin, self).get_urls()

        info = self.model._meta.app_label, self.model._meta.model_name
        myurls = [
            re_path(r'^(?P<object_pk>.+)/permissions/(?P<user_id>\-?\d+)/remove/$',
                view=self.admin_site.admin_view(
                    self.obj_perms_delete),name='%s_%s_permissions_delete' % info)
        ]
        urls = myurls + urls
        
        return urls

    def obj_perms_manage_view(self, request, object_pk):
        """
        Main object permissions view. Presents all users and groups with any
        object permissions for the current model *instance*. Users or groups
        without object permissions for related *instance* would **not** be
        shown. In order to add or manage user or group one should use links or
        forms presented within the page.
        """

        from guardian.shortcuts import assign_perm
        from guardian.shortcuts import get_user_model
        from guardian.shortcuts import get_users_with_perms
        from collections import OrderedDict
        from django.contrib.admin.utils import unquote
        from django.shortcuts import redirect

        if not self.has_change_permission(request, None):
            post_url = reverse('admin:index', current_app=self.admin_site.name)
            return redirect(post_url)

        obj = get_object_or_404(self.get_queryset(
            request), pk=unquote(object_pk))
        users_perms = OrderedDict(
            sorted(
                get_users_with_perms(obj, attach_perms=True,
                                     with_group_users=False).items(),
                key=lambda user: getattr(
                    user[0], get_user_model().USERNAME_FIELD)
            )
        )

        if request.method == 'POST' and 'submit_manage_user' in request.POST:
            perm = '{}.change_{}'.format(self.model._meta.app_label, self.model._meta.model_name)
            user = User.objects.get(username=request.POST['user'])
            assign_perm(perm, user, obj)
            user_form = self.get_obj_perms_user_select_form(request)(request.POST)
            group_form = self.get_obj_perms_group_select_form(request)(request.POST)
            info = (
                self.admin_site.name,
                self.model._meta.app_label,
                self.model._meta.model_name,
            )
            if user_form.is_valid():
                user_id = user_form.cleaned_data['user'].pk
                messages.success(request, 'Permissions saved.')
                if not request.POST.get('is_permanent', False): # If "Grant indefinitely" not selected remove permission after 24 h
                    delete_obj_perm_after_24h(perm, user.id, obj.id, obj._meta.app_label, obj._meta.model_name)
                return HttpResponseRedirect(".")
        else:
            user_form = self.get_obj_perms_user_select_form(request)()

        context = self.get_obj_perms_base_context(request, obj)
        context['users_perms'] = users_perms
        context['user_form'] = user_form

        # https://github.com/django/django/commit/cf1f36bb6eb34fafe6c224003ad585a647f6117b
        request.current_app = self.admin_site.name

        return render(request, self.get_obj_perms_manage_template(), context)

    def obj_perms_manage_user_view(self, request, object_pk, user_id):
        """
        Forbid usage of this view
        """

        raise PermissionDenied

    def get_obj_perms_user_select_form(self, request):
        """
        Returns form class for selecting a user for permissions management.  By
        default :form:`UserManage` is returned.
        """
        
        return CustomUserManage

    def obj_perms_delete(self, request, object_pk, user_id):
        """ Delete object permission for a user"""

        from guardian.shortcuts import get_user_model
        from guardian.shortcuts import remove_perm

        user = get_object_or_404(get_user_model(), pk=user_id)
        obj = get_object_or_404(self.get_queryset(request), pk=object_pk)
        
        remove_perm('{}.change_{}'.format(self.model._meta.app_label, self.model._meta.model_name),  user, obj)
        messages.success(request, 'Permission removed.')

        return HttpResponseRedirect("../..")

#################################################
#             CUSTOM SEARCH OPTIONS             #
#################################################

class FieldUse(StrField):

    name = 'use'
    
    def get_lookup_name(self):
        return 'us_e'

class FieldLocation(StrField):

    name = 'location'

    def get_lookup_name(self):
        return 'l_ocation'

class FieldApplication(StrField):

    name = 'application'

    def get_lookup_name(self):
        return 'a_pplication'

class FieldCreated(DateTimeField):

    name = 'created_timestamp'

    def get_lookup_name(self):
        return 'created_date_time'

class FieldLastChanged(DateTimeField):

    name = 'last_changed_timestamp'

    def get_lookup_name(self):
        return 'last_changed_date_time'

class FieldIntegratedPlasmidM2M(IntField):
    
    name = 'integrated_plasmids_id'

    def get_lookup_name(self):
        return 'integrated_plasmids__id'

class FieldCassettePlasmidM2M(IntField):
    
    name = 'cassette_plasmids_id'

    def get_lookup_name(self):
        return 'cassette_plasmids__id'

class FieldEpisomalPlasmidM2M(IntField):
    
    name = 'episomal_plasmids_id'
    
    def get_lookup_name(self):
        return 'episomal_plasmids__id'

class FieldFormZProject(StrField):
    
    name = 'formz_projects_title'
    suggest_options = True

    def get_options(self, search):
        return FormZProject.objects.all().values_list('short_title', flat=True)

    def get_lookup_name(self):
        return 'formz_projects__short_title'
    
class FieldParent1(IntField):

    name = 'parent_1_id'
    
    def get_lookup_name(self):
        return 'parent_1__id'

class FieldParent2(IntField):

    name = 'parent_2_id'

    def get_lookup_name(self):
        return 'parent_2__id'

#################################################
#          DOWNLOAD FORMBLATT Z ACTION          #
#################################################

def formz_as_html(modeladmin, request, queryset):

    """Export ForblattZ as html """

    from django.template.loader import get_template
    from bs4 import BeautifulSoup
    import zipfile
    from django.http import HttpResponse

    def get_params(app_label, model_name, obj_id):
        from formz.models import FormZStorageLocation
        from formz.models import FormZHeader
        from django.apps import apps
        from django.contrib.contenttypes.models import ContentType
        from formz.models import ZkbsCellLine

        model = apps.get_model(app_label, model_name)
        model_content_type = ContentType.objects.get(app_label=app_label, model=model_name)
        opts = model._meta
        obj = model.objects.get(id=int(obj_id))
        
        # Get storage location object or create a new 'empty' one
        if FormZStorageLocation.objects.get(collection_model=model_content_type):
            storage_location = FormZStorageLocation.objects.get(collection_model=model_content_type)
        else:
            storage_location = FormZStorageLocation(
                collection_model = None,
                storage_location = None,
                species_name = None,
                species_risk_group = None
            )

        if FormZHeader.objects.all().first():
            formz_header = FormZHeader.objects.all().first()
        else:
            formz_header = None

        obj.common_formz_elements = obj.get_all_common_formz_elements()
        obj.uncommon_formz_elements =  obj.get_all_uncommon_formz_elements()
        obj.instock_plasmids = obj.get_all_instock_plasmids()
        obj.transient_episomal_plasmids = obj.get_all_transient_episomal_plasmids()

        if model_name == 'cellline':
            storage_location.species_name = obj.organism
            storage_location.species_name_str = obj.organism.name_for_search
            storage_location.species_risk_group = obj.organism.risk_group
            obj.s2_plasmids = obj.celllineepisomalplasmid_set.all().filter(s2_work_episomal_plasmid=True).distinct().order_by('id')
            transfected = True
            try:
                virus_packaging_cell_line = ZkbsCellLine.objects.filter(name__iexact='293T (HEK 293T)').order_by('id')[0]
            except:
                virus_packaging_cell_line = ZkbsCellLine(name = '293T (HEK 293T)')
        elif model_name == 'wormstrain':
            transfected = False
            virus_packaging_cell_line = None
            storage_location.species_name_str = obj.get_organism_display()
        else:
            storage_location.species_name_str = storage_location.species_name.name_for_search
            obj.s2_plasmids = None
            transfected = False
            virus_packaging_cell_line = None

        params = {'object': obj,
                'storage_location': storage_location,
                'formz_header': formz_header,
                'transfected': transfected,
                'virus_packaging_cell_line': virus_packaging_cell_line,
                }

        return params

    response = HttpResponse(content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="formblattz_{}_{}.zip'.format(time.strftime("%Y%m%d"), time.strftime("%H%M%S"))

    template = get_template('admin/formz/formz_for_export.html')
    app_label = queryset[0]._meta.app_label
    model_name = queryset[0].__class__.__name__

    # Generates zip file

    with zipfile.ZipFile(response, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for obj in queryset:
            params = get_params(app_label, model_name.lower(), obj.id)
            params['map_attachment_type'] = request.POST.get('map_attachment_type', default='none')
            html = template.render(params)
            html = BeautifulSoup(html, features="lxml")
            html = html.prettify("utf-8")
            zip_file.writestr('{}_{}.html'.format(model_name, obj.id), html)
        
    return response

formz_as_html.short_description = "Export Formblatt Z for selected items"