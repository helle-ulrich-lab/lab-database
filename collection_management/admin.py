# -*- coding: utf-8 -*-

from __future__ import unicode_literals

#################################################
#    DJANGO 'CORE' FUNCTIONALITIES IMPORTS      #
#################################################

from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.admin import UserAdmin

from django.apps import apps
from django.db import models

from django.urls import reverse
from django.core.mail import send_mail, mail_admins
from django.utils import timezone
from django.core.exceptions import PermissionDenied

from django.utils.translation import ugettext as _, ugettext_lazy
from django.utils.text import capfirst

from django.forms import TextInput
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.urls import reverse

from django_project.settings import MEDIA_ROOT
from django_project.settings import BASE_DIR
from django_project.private_settings import SAVERIS_USERNAME
from django_project.private_settings import SAVERIS_PASSWORD

from django.contrib.auth.models import Group, User
from django.contrib.auth.admin import GroupAdmin, UserAdmin

from django.contrib.admin.utils import unquote
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.utils.encoding import force_text
from django.shortcuts import get_object_or_404, render
from django.utils.safestring import mark_safe

#################################################
#        ADDED FUNCTIONALITIES IMPORTS          #
#################################################

# Advanced search functionalities from DjangoQL
from djangoql.admin import DjangoQLSearchMixin
from djangoql.schema import DjangoQLSchema, StrField

# Object history tracking from django-simple-history
from simple_history.admin import SimpleHistoryAdmin

# Import/Export functionalities from django-import-export
from import_export import resources

# Background tasks
from background_task import background

# Http stuff
import http.cookiejar
import urllib.request, urllib.parse, urllib.error

# Django guardian
from guardian.admin import GuardedModelAdmin
from guardian.admin import UserManage

#################################################
#                OTHER IMPORTS                  #
#################################################

import datetime
import inspect
from snapgene.pyclasses.client import Client
from snapgene.pyclasses.config import Config
import zmq
import os
import time

#################################################
#               CUSTOM FUNCTIONS                #
#################################################

@background(schedule=1) # Run snapgene_plasmid_map_preview 1 s after it is called, as "background" process
def snapgene_plasmid_map_preview(plasmid_map_path, png_plasmid_map_path, gbk_plasmid_map_path, obj_id, obj_name):
    """ Given a path to a snapgene plasmid map, use snapegene server
    to detect common features and create map preview as png
    and """

    try:
        config = Config()
        server_ports = config.get_server_ports()
        for port in server_ports.values():
            try:
                client = Client(port, zmq.Context())
            except:
                continue
            break
        
        common_features_path = os.path.join(BASE_DIR, "snapgene/standardCommonFeatures.ftrs")
        
        argument = {"request":"detectFeatures", "inputFile": plasmid_map_path, 
        "outputFile": plasmid_map_path, "featureDatabase": common_features_path}
        client.requestResponse(argument, 10000)                       
        
        argument = {"request":"generatePNGMap", "inputFile": plasmid_map_path,
        "outputPng": png_plasmid_map_path, "title": "pHU{} - {}".format(obj_id, obj_name),
        "showEnzymes": True, "showFeatures": True, "showPrimers": True, "showORFs": False}
        client.requestResponse(argument, 10000)
        
        argument = {"request":"exportDNAFile", "inputFile": plasmid_map_path,
        "outputFile": gbk_plasmid_map_path, "exportFilter": "biosequence.gb"}
        client.requestResponse(argument, 10000)

    except:
        mail_admins("Snapgene server error", "There was an error with creating the preview for {} with snapgene server".format(dna_plasmid_map_path), fail_silently=True)
        raise Exception

@background(schedule=86400) # Run snapgene_plasmid_map_preview 1 s after it is called, as "background" process
def delete_obj_perm_after_24h(perm, user_id, obj_id, app_label, model_name):
    """ Delete object permession after 24 h"""
    
    from django.apps import apps
    from guardian.shortcuts import remove_perm
    
    user = User.objects.get(id=user_id)
    obj = apps.get_model(app_label, model_name).objects.get(id=obj_id)

    remove_perm(perm, user, obj)

#################################################
#                CUSTOM CLASSES                 #
#################################################

class Approval():
    def approval(self, instance):
        if instance.last_changed_approval_by_pi is not None:
            return instance.last_changed_approval_by_pi
        else:
            return instance.created_approval_by_pi
    approval.boolean = True
    approval.short_description = "Approved"

USER_NATURAL_KEY = tuple(
    key.lower() for key in settings.AUTH_USER_MODEL.split('.', 1))

class SimpleHistoryWithSummaryAdmin(SimpleHistoryAdmin):
    
    object_history_template = "admin/object_history.html"
    
    def history_view(self, request, object_id, extra_context=None):
        """The 'history' admin view for this model."""

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
        history_list_display = getattr(self, "history_list_display", [])
        # If no history was found, see whether this object even exists.
        try:
            obj = self.get_queryset(request).get(**{pk_name: object_id})
        except model.DoesNotExist:
            try:
                obj = action_list.latest('history_date').instance
            except action_list.model.DoesNotExist:
                raise http.Http404

        if not self.has_change_permission(request, obj):
            raise PermissionDenied

        # Set attribute on each action_list entry from admin methods
        for history_list_entry in history_list_display:
            value_for_entry = getattr(self, history_list_entry, None)
            if value_for_entry and callable(value_for_entry):
                for list_entry in action_list:
                    setattr(list_entry, history_list_entry,
                            value_for_entry(list_entry))

        # Create data structure for history summary
        history_summary_data = []
        try:
            history_summary = obj.history.all()
            if len(history_summary) > 1:
                history_pairs = pairwise(history_summary)
                for history_element in history_pairs:
                    delta = history_element[0].diff_against(history_element[1])
                    if delta:
                        changes_list = []
                        changes = delta.changes
                        if delta.changes:
                            for change in delta.changes:
                                if not change.field.endswith(("time", "_pi")): # Do not show created/changed date/time or approval by PI fields
                                    field_name = model._meta.get_field(change.field).verbose_name
                                    changes_list.append(
                                        (field_name.replace("_", " ").capitalize(), 
                                        change.old if change.old else 'None', 
                                        change.new if change.new else 'None'))
                            if changes_list:
                                history_summary_data.append(
                                    (history_element[0].last_changed_date_time, 
                                    User.objects.get(id=int(history_element[0].history_user_id)), 
                                    changes_list))
        except:
            pass

        content_type = ContentType.objects.get_by_natural_key(
            *USER_NATURAL_KEY)
        admin_user_view = 'admin:%s_%s_change' % (content_type.app_label,
                                                  content_type.model)
        context = {
            'title': _('Change history: %s') % force_text(obj),
            'action_list': action_list,
            'module_name': capfirst(force_text(opts.verbose_name_plural)),
            'object': obj,
            'root_path': getattr(self.admin_site, 'root_path', None),
            'app_label': app_label,
            'opts': opts,
            'admin_user_view': admin_user_view,
            'history_list_display': history_list_display,
            'history_summary_data': history_summary_data,
        }
        context.update(extra_context or {})
        extra_kwargs = {}
        return render(request, self.object_history_template, context,
                      **extra_kwargs)

class DataLoggerWebsiteLogin(object):

    """ Class to log on to the Saveris website with 
    username and password """

    def __init__(self, login, password):

        self.login = login
        self.password = password

        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPRedirectHandler(),
            urllib.request.HTTPHandler(debuglevel=0),
            urllib.request.HTTPSHandler(debuglevel=0),
            urllib.request.HTTPCookieProcessor(self.cj)
        )
        self.opener.addheaders = [
            ('User-agent', ('Mozilla/4.0 (compatible; MSIE 6.0; '
                           'Windows NT 5.2; .NET CLR 1.1.4322)'))
        ]
        self.loginToWebsite()

    def loginToWebsite(self):
        """ Handle login. This should populate our cookie jar """
        login_data = urllib.parse.urlencode({
            'data[User][login]' : self.login,
            'data[User][password]' : self.password,
        }).encode("utf-8")
        
        response = self.opener.open("https://www.saveris.net/users/login", login_data)
        return ''.join(str(response.readlines()))

class CustomUserManage(UserManage):
    
    """
    Add drop-down menu to select user to who to give additonal permissions
    """

    from django import forms

    user = forms.ChoiceField(choices=[('------', '------')] + [(u.username, u) for u in User.objects.all().order_by('last_name') if u.groups.filter(name='Regular lab member').exists()],
                            label=_("Username"),
                        error_messages={'does_not_exist': _(
                            "This user does not exist")},)
    is_permanent = forms.BooleanField(required=False, label=_("Grant indefinitely?"))

class CustomGuardedModelAdmin(GuardedModelAdmin):

    def get_urls(self):
        """
        Extends standard guardian admin model urls with delete url
        """
        
        from django.conf.urls import url
        
        urls = super(CustomGuardedModelAdmin, self).get_urls()

        info = self.model._meta.app_label, self.model._meta.model_name
        myurls = [
            url(r'^(?P<object_pk>.+)/permissions/(?P<user_id>\-?\d+)/remove/$',
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

import django.contrib.admin.widgets
class CustomRelatedFieldWidgetWrapper(django.contrib.admin.widgets.RelatedFieldWidgetWrapper):
    """Monkey patch CustomRelatedFieldWidgetWrapper to show
    eye next to change icon"""
    template_name = 'admin/related_widget_wrapper_custom.html'
django.contrib.admin.widgets.RelatedFieldWidgetWrapper = CustomRelatedFieldWidgetWrapper

#################################################
#               CUSTOM ADMIN SITE               #
#################################################

class MyAdminSite(admin.AdminSite):
    '''Create a custom admin site called MyAdminSite'''
    
    # Text to put at the end of each page's <title>.
    site_title = ugettext_lazy('Ulrich Lab Intranet')

    # Text to put in each page's <h1>.
    site_header = ugettext_lazy('Ulrich Lab Intranet')

    # Text to put at the top of the admin index page.
    index_title = ugettext_lazy('Home')

    # URL for the "View site" link at the top of each admin page.
    site_url = '/'

    def get_urls(self):
        
        from django.conf.urls import url
        
        urls = super(MyAdminSite, self).get_urls()
        # Note that custom urls get pushed to the list (not appended)
        # This doesn't work with urls += ...
        urls = [
            url(r'^approval_summary/$', self.admin_view(self.approval_summary)),
            url(r'^approval_summary/approve$', self.admin_view(self.approve_approval_summary)),
            url(r'^order_management/my_orders_redirect$', self.admin_view(self.my_orders_redirect)),
            url(r'uploads/(?P<url_path>.*)$', self.admin_view(self.uploads)),
            url(r'^temp_control/$', self.temp_control),
        ] + urls
        return urls

    def approval_summary(self, request):
        """ View to show all added and changed records from 
        collection_management that have been added or changed
        and that need to be approved by Helle"""
        
        from django.shortcuts import render
        from django.apps import apps

        if request.user.is_superuser or request.user.id == 6: # Only allow superusers and Helle to access the page
            data = []
            order_model = apps.get_app_config('order_management').get_model("order")
            added = order_model.objects.all().filter(created_approval_by_pi=False)
            if added:
                data.append(
                    (str(order_model._meta.verbose_name_plural).capitalize(),
                    str(order_model.__name__).lower(), 
                    list(added.only('id','part_description','created_by')),
                    [],
                    str(order_model._meta.app_label)
                    ))
            app = apps.get_app_config('collection_management')
            for model in app.models.values():
                if model._meta.verbose_name.lower().startswith(("strain", "plasmid", "oligo", "mammmalian")): # Skip certain models within collection_management
                    added = model.objects.all().filter(created_approval_by_pi=False)
                    changed = model.objects.all().filter(last_changed_approval_by_pi=False).exclude(id__in=added)
                    if added or changed:
                        data.append(
                            (str(model._meta.verbose_name_plural).capitalize(),
                            str(model.__name__).lower(), 
                            list(added.only('id','name','created_by')),
                            list(changed.only('id','name','created_by')),
                            str(model._meta.app_label),
                            ))
            context = {
            'user': request.user,
            'site_header': self.site_header,
            'has_permission': self.has_permission(request), 
            'site_url': self.site_url, 
            'title':"Records to be approved", 
            'data':data
            }
            return render(request, 'admin/approval_summary.html', context)
        else:
            return messages.error(request, 'Nice try, you are not allowed to do that.')
            
    def approve_approval_summary(self, request):
        """ Approve all records that are pending approval """

        if request.user.id == 6: # Only allow Helle to approve records
            try:
                app = apps.get_app_config('collection_management')
                for model in app.models.values():
                    if not model._meta.verbose_name.lower().startswith(("historical", "antibody", "mammalian cell line document")): # Skip certain models within collection_management 
                        model.objects.all().filter(created_approval_by_pi=False).update(created_approval_by_pi=True, approval_by_pi_date_time = timezone.now())
                        model.objects.all().filter(last_changed_approval_by_pi=False).update(last_changed_approval_by_pi=True, approval_by_pi_date_time = timezone.now())
                order_model = apps.get_app_config('order_management').get_model("order")
                order_model.objects.all().filter(created_approval_by_pi=False).update(created_approval_by_pi=True)
                messages.success(request, 'The records have been approved')
                return HttpResponseRedirect("/approval_summary/")
            except Exception as err:
                messages.error(request, 'The records could not be approved. Error: ' + str(err))
                return HttpResponseRedirect("/approval_summary/")
        else:
            messages.error(request, 'Nice try, you are not allowed to do that.')
            return HttpResponseRedirect("/approval_summary/")

    def my_orders_redirect(self, request):
        """ Redirect user to their My Orders page """

        return HttpResponseRedirect('/order_management/order/?q=created_by.username+%3D+"{}"'.format(request.user.username))

    def uploads(self, request, *args, **kwargs):
        """Protected view for uploads/media files"""

        from django.http import HttpResponse
        from django.http import Http404
        import re
        from django.core.files.storage import default_storage
        import mimetypes
        
        url_path = str(kwargs["url_path"])
        
        if default_storage.exists(url_path): # check if file exists
            
            response = HttpResponse()
            mimetype, encoding = mimetypes.guess_type(url_path)
            mimetype = mimetype if mimetype else 'application/octet-stream'
            response["Content-Type"] = mimetype
            if encoding:
                response["Content-Encoding"] = encoding
            
            if url_path.startswith('collection_management') and not url_path.endswith('png'):
                if '/huplasmid/' in url_path:
                    try:
                        app_name, model_name, file_type, file_name = url_path.split('/')
                        file_prefix = file_name.split('_')[0]
                        file_ext = file_name.split('.')[-1]
                        model = apps.get_model(app_name, model_name)
                        obj_id = int(re.findall('\d+(?=_)', file_name)[0])
                    except:
                        raise Http404()
                else:
                    try:
                        app_name, model_name, file_name = url_path.split('/')
                        file_prefix = file_name.split('_')[0]
                        file_ext = file_name.split('.')[-1]
                        model = apps.get_model(app_name, model_name)
                        obj_id = int(re.findall('\d+(?=_)', file_name)[0])
                    except:
                        raise Http404()

                if model_name == 'mammalianlinedoc':
                    mammalianline = apps.get_model(app_name, "mammalianline")
                    obj_name = mammalianline.objects.get(id=obj_id).name + " Test #" + re.findall('\d+(?=.)', file_name)[-1]
                else:
                    obj_name = model.objects.get(id=obj_id).name

                download_file_name = "{file_prefix} - {obj_name}.{file_ext}".format(
                    file_prefix = file_prefix,
                    obj_name = obj_name,
                    file_ext = file_ext,
                    ).replace(',','')

                if 'pdf' in mimetype.lower():
                    response["Content-Disposition"] = "inline; filename={download_file_name}".format(download_file_name=download_file_name)
                else:
                    response["Content-Disposition"] = "attachment; filename={download_file_name}".format(download_file_name=download_file_name)
            else:
                file_name = os.path.basename(url_path)
                if 'pdf' in mimetype.lower():
                    response["Content-Disposition"] = "inline; filename={download_file_name}".format(download_file_name=file_name)
                elif 'png' in mimetype.lower():
                    response["Content-Disposition"] = ""
                else:
                    response["Content-Disposition"] = "attachment; filename={download_file_name}".format(download_file_name=file_name)
            
            response['X-Accel-Redirect'] = "/secret/{url_path}".format(url_path=url_path)
            return response
        else:
            raise Http404

    def temp_control(self, request):
        """ View to show the temperature of the -150° freezer """

        from bs4 import BeautifulSoup
        from django.shortcuts import render

        # Log on to the Saveris website, browse to page that shows T and read response
        html = DataLoggerWebsiteLogin(SAVERIS_USERNAME, SAVERIS_PASSWORD).opener.open('https://www.saveris.net/MeasuringPts').read()

        soup = BeautifulSoup(html)
        
        # Get all td elements, extract relevant info and style it a bit
        td_elements = soup.find_all('td')
        T = td_elements[4].text.strip().replace(",", ".").replace("Â", "").replace("°", "° ")
        date_time = datetime.datetime.strptime(td_elements[5].text.strip(), '%d.%m.%Y %H:%M:%S')

        context = {
        'user': request.user,
        'site_header': self.site_header,
        'has_permission': self.has_permission(request), 
        'site_url': self.site_url, 
        'title':"Temperature control", 
        'data':[date_time, T]
        }
        
        return render(request, 'admin/temp_control.html', context)

# Instantiate custom admin site 
my_admin_site = MyAdminSite()

# Disable delete selected action
my_admin_site.disable_action('delete_selected')

#################################################
#          CUSTOM USER SEARCH OPTIONS           #
#################################################

class SearchFieldOptUsername(StrField):
    """Create a list of unique users' usernames for search"""

    model = User
    name = 'username'
    suggest_options = True

    def get_options(self):
        """exclude(id__in=[1,20]) removes admin and guest accounts from 
        the list of options, distinct() returns only unique values
        sorted in alphabetical order"""

        return super(SearchFieldOptUsername, self).get_options().\
        exclude(id__in=[1,20,36,]).\
        distinct().\
        order_by(self.name).\
        values_list(self.name, flat=True)

class SearchFieldOptLastname(StrField):
    """Create a list of unique user's last names for search"""

    model = User
    name = 'last_name'
    suggest_options = True

    def get_options(self):
        """exclude(id__in=[1,20]) removes admin and guest accounts from 
        the list of options, distinct() returns only unique values
        sorted in alphabetical order"""
        
        return super(SearchFieldOptLastname, self).\
        get_options().\
        exclude(id__in=[1,20]).\
        distinct().order_by(self.name).\
        values_list(self.name, flat=True)

#################################################
#          SA. CEREVISIAE STRAIN PAGES          #
#################################################

from .models import SaCerevisiaeStrain as collection_management_SaCerevisiaeStrain

class SaCerevisiaeStrainQLSchema(DjangoQLSchema):
    '''Customize search functionality'''
    
    include = (collection_management_SaCerevisiaeStrain, User) # Include only the relevant models to be searched

    def get_fields(self, model):
        ''' Define fields that can be searched'''
        
        if model == collection_management_SaCerevisiaeStrain:
            return ['id', 'name', 'relevant_genotype', 'mating_type', 'chromosomal_genotype', 'parental_strain',
                'construction', 'modification', 'plasmids', 'selection', 'phenotype', 'background', 'received_from',
                'us_e', 'note', 'reference', 'created_by',]
        elif model == User:
            return [SearchFieldOptUsername(), SearchFieldOptLastname()]
        return super(SaCerevisiaeStrainQLSchema, self).get_fields(model)

class SaCerevisiaeStrainExportResource(resources.ModelResource):
    """Defines a custom export resource class for SaCerevisiaeStrain"""
    
    class Meta:
        model = collection_management_SaCerevisiaeStrain
        fields = ('id', 'name', 'relevant_genotype', 'mating_type', 'chromosomal_genotype', 'parental_strain',
        'construction', 'modification', 'plasmids', 'selection', 'phenotype', 'background', 'received_from',
        'us_e', 'note', 'reference', 'created_date_time', 'last_changed_date_time', 'created_by__username',)

def export_sacerevisiaestrain(modeladmin, request, queryset):
    """Export SaCerevisiaeStrain as xlsx"""

    export_data = SaCerevisiaeStrainExportResource().export(queryset)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="{}_{}_{}.xlsx'.format(collection_management_SaCerevisiaeStrain.__name__, time.strftime("%Y%m%d"), time.strftime("%H%M%S"))
    response.write(export_data.xlsx)
    return response
export_sacerevisiaestrain.short_description = "Export selected strains as xlsx"

class SaCerevisiaeStrainPage(DjangoQLSearchMixin, SimpleHistoryWithSummaryAdmin, CustomGuardedModelAdmin, Approval):
    list_display = ('id', 'name', 'mating_type','created_by', 'approval')
    list_display_links = ('id', )
    list_per_page = 25
    formfield_overrides = {models.CharField: {'widget': TextInput(attrs={'size':'93'})},} # Make TextInput fields wider
    djangoql_schema = SaCerevisiaeStrainQLSchema
    actions = [export_sacerevisiaestrain]

    search_fields = ['id', 'name']
    autocomplete_fields = ['parent_1', 'parent_2', 'integrated_plasmids', 'cassette_plasmids']
    
    def save_model(self, request, obj, form, change):
        '''Override default save_model to limit a user's ability to save a record
        Superusers and lab managers can change all records
        Regular users can change only their own records
        Guests cannot change any record'''
        
        if obj.pk == None:
            obj.created_by = request.user
            obj.save()
        else:
            saved_obj = collection_management_SaCerevisiaeStrain.objects.get(pk=obj.pk)
            if request.user.is_superuser or request.user == saved_obj.created_by or request.user.groups.filter(name='Lab manager').exists() or saved_obj.created_by.groups.filter(name='Past member').exists() or saved_obj.created_by.id == 6:
                obj.last_changed_approval_by_pi = False
                obj.save()
            else:
                raise PermissionDenied
    
    def get_readonly_fields(self, request, obj=None):
        '''Override default get_readonly_fields to define user-specific read-only fields
        If a user is not a superuser, lab manager or the user who created a record
        return all fields as read-only
        'created_date_time' and 'last_changed_date_time' fields must always be read-only
        because their set by Django itself'''
        
        if obj:
            if (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by):
                return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by',]
            else:
                if request.user.has_perm('collection_management.change_sacerevisiaestrain', obj):
                    return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by',]
                if obj.created_by.groups.filter(name='Past member') or obj.created_by.id == 6:
                    return ['name', 'relevant_genotype', 'mating_type', 'chromosomal_genotype', 'parental_strain',
                'construction', 'modification', 'plasmids', 'selection', 'phenotype', 'background', 'received_from',
                'us_e', 'reference', 'created_date_time', 'created_approval_by_pi', 'last_changed_date_time',
                'last_changed_approval_by_pi', 'created_by',]
                else:
                    return ['name', 'relevant_genotype', 'mating_type', 'chromosomal_genotype', 'parental_strain',
                    'construction', 'modification', 'plasmids', 'selection', 'phenotype', 'background', 'received_from',
                    'us_e', 'note', 'reference', 'created_date_time', 'created_approval_by_pi', 'last_changed_date_time',
                    'last_changed_approval_by_pi', 'created_by',]
        else:
            return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi',]
    
    def get_form(self, request, obj=None, **kwargs):
        """
        Modify the default factory to change form fields based on the request/object.
        """
        default_factory = super(SaCerevisiaeStrainPage, self).get_form(request, obj=obj, **kwargs)

        def factory(*args, **_kwargs):
            form = default_factory(*args, **_kwargs)
            return self.modify_form(form, request, obj, **_kwargs)

        return factory

    @staticmethod
    def modify_form(form, request, obj, **kwargs):
        """
        Edit 'parental_line' field
        """
        if obj:
            if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by) or request.user.groups.filter(name='Guest').exists():
                if not request.user.has_perm('collection_management.change_sacerevisiaestrain', obj):
                    for field in ['parent_1', 'parent_2', 'integrated_plasmids', 'cassette_plasmids']:
                        try:
                            form.fields[field].disabled = True
                        except:
                            continue
        return form


    def add_view(self,request,extra_content=None):
        '''Override default add_view to show only desired fields'''
        
        self.fields = ('name', 'relevant_genotype', 'mating_type', 'chromosomal_genotype', 'parent_1', 'parent_2', 
        'parental_strain', 'construction', 'modification','integrated_plasmids', 'cassette_plasmids', 'plasmids', 
        'selection', 'phenotype', 'background', 'received_from', 'us_e', 'note', 'reference',)
        return super(SaCerevisiaeStrainPage,self).add_view(request)

    def change_view(self,request,object_id,extra_content=None):
        '''Override default change_view to show only desired fields'''
        
        self.fields = ('name', 'relevant_genotype', 'mating_type', 'chromosomal_genotype', 'parent_1', 'parent_2', 
        'parental_strain', 'construction', 'modification', 'integrated_plasmids', 'cassette_plasmids', 'plasmids', 
        'selection', 'phenotype', 'background', 'received_from','us_e', 'note', 'reference', 'created_date_time', 
        'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by',)
        return super(SaCerevisiaeStrainPage,self).change_view(request,object_id)
    
    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        """Override default changeform_view to hide Save buttons when certain conditions (same as
        those in get_readonly_fields method) are met"""

        extra_context = extra_context or {}
        extra_context['show_submit_line'] = True
        if object_id:
            obj = collection_management_SaCerevisiaeStrain.objects.get(pk=object_id)
            if obj:
                if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by or obj.created_by.groups.filter(name='Past member'))  or request.user.groups.filter(name='Guest').exists():
                    if not request.user.has_perm('collection_management.change_sacerevisiaestrain', obj):
                        extra_context['show_submit_line'] = False
        return super(SaCerevisiaeStrainPage, self).changeform_view(request, object_id, extra_context=extra_context)

    def obj_perms_manage_view(self, request, object_pk):
        """
        Main object Guardian permissions view. 

        Customized to allow only record owner to change permissions
        """
        obj = collection_management_SaCerevisiaeStrain.objects.get(pk=object_pk)
        
        if obj:
            if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by) or request.user.groups.filter(name='Guest').exists():
                messages.error(request, 'Nice try, you are allowed to change the permissions of your own records only.')
                return HttpResponseRedirect("..")
        return super(SaCerevisiaeStrainPage,self).obj_perms_manage_view(request, object_pk)


my_admin_site.register(collection_management_SaCerevisiaeStrain, SaCerevisiaeStrainPage)

#################################################
#               HU PLASMID PAGES                #
#################################################

from .models import HuPlasmid as collection_management_HuPlasmid

class HuPlasmidQLSchema(DjangoQLSchema):
    '''Customize search functionality'''
    
    include = (collection_management_HuPlasmid, User) # Include only the relevant models to be searched

    def get_fields(self, model):
        '''Define fields that can be searched'''
        
        if model == collection_management_HuPlasmid:
            return ['id', 'name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 'note', 
                'reference', 'created_by',]
        elif model == User:
            return [SearchFieldOptUsername(), SearchFieldOptLastname()]
        return super(HuPlasmidQLSchema, self).get_fields(model)

class HuPlasmidExportResource(resources.ModelResource):
    """Defines a custom export resource class for HuPlasmid"""
    
    class Meta:
        model = collection_management_HuPlasmid
        fields = ('id', 'name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 'note', 
                'reference', 'plasmid_map', 'created_date_time', 'last_changed_date_time', 'created_by__username',)

def export_huplasmid(modeladmin, request, queryset):
    """Export HuPlasmid as xlsx"""

    export_data = HuPlasmidExportResource().export(queryset)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="{}_{}_{}.xlsx'.format(collection_management_HuPlasmid.__name__, time.strftime("%Y%m%d"), time.strftime("%H%M%S"))
    response.write(export_data.xlsx)
    return response
export_huplasmid.short_description = "Export selected plasmids as xlsx"

class HuPlasmidPage(DjangoQLSearchMixin, SimpleHistoryWithSummaryAdmin, CustomGuardedModelAdmin, Approval):
    list_display = ('id', 'name', 'selection', 'get_plasmidmap_short_name', 'created_by', 'approval')
    list_display_links = ('id', )
    list_per_page = 25
    formfield_overrides = {models.CharField: {'widget': TextInput(attrs={'size':'93'})},} # Make TextInput fields wider
    djangoql_schema = HuPlasmidQLSchema
    actions = [export_huplasmid]
    filter_horizontal = ['formz_elements',]
    search_fields = ['id', 'name']
    
    def save_model(self, request, obj, form, change):
        '''Override default save_model to limit a user's ability to save a record
        Superusers and lab managers can change all records
        Regular users can change only their own records
        Guests cannot change any record.
        It also renames a plasmid map to pNZ{obj.id}_{date_created}_{time_created}.ext
        and whenever possible creates a plasmid map preview with snapegene server'''
        
        rename_and_preview = False
        new_obj = False

        if obj.pk == None:
            obj.created_by = request.user
            if obj.plasmid_map:
                rename_and_preview = True
                new_obj = True
            obj.save()
        else:
            old_obj = collection_management_HuPlasmid.objects.get(pk=obj.pk)
            if request.user.is_superuser or request.user == old_obj.created_by or request.user.groups.filter(name='Lab manager').exists():
                obj.last_changed_approval_by_pi = False
                if obj.plasmid_map and obj.plasmid_map != old_obj.plasmid_map:
                    rename_and_preview = True
                    obj.save_without_historical_record()
                else:
                    obj.save()
            else:
                if obj.created_by.id == 6: # Allow saving object, if record belongs to Helle (user id = 6)
                    obj.last_changed_approval_by_pi = False
                    if obj.plasmid_map and obj.plasmid_map != old_obj.plasmid_map:
                        rename_and_preview = True
                        obj.save_without_historical_record()
                    else:
                        obj.save()
                else:
                    raise PermissionDenied
        
        # Rename plasmid map
        if rename_and_preview:
            plasmid_map_dir_path = os.path.join(MEDIA_ROOT, 'collection_management/huplasmid/dna/')
            old_file_name_abs_path = os.path.join(MEDIA_ROOT, obj.plasmid_map.name)
            old_file_name, ext = os.path.splitext(os.path.basename(old_file_name_abs_path)) 
            new_file_name = os.path.join(
                'collection_management/huplasmid/dna/', 
                "pHU{}_{}_{}{}".format(obj.id, time.strftime("%Y%m%d"), time.strftime("%H%M%S"), ext.lower()))
            new_file_name_abs_path = os.path.join(MEDIA_ROOT, new_file_name)
            
            if not os.path.exists(plasmid_map_dir_path):
                os.makedirs(plasmid_map_dir_path) 
            
            os.rename(
                old_file_name_abs_path, 
                new_file_name_abs_path)
            
            obj.plasmid_map.name = new_file_name
            obj.plasmid_map_png.name = new_file_name.replace("huplasmid/dna", "huplasmid/png").replace(".dna", ".png")
            obj.plasmid_map_gbk.name = new_file_name.replace("huplasmid/dna", "huplasmid/gbk").replace(".dna", ".gbk")
            obj.save()

            # For new records, delete first history record, which contains the unformatted plasmid_map name, and change 
            # the newer history record's history_type from changed (~) to created (+). This gets rid of a duplicate
            # history record created when automatically generating a plasmid_map name
            if new_obj:
                obj.history.last().delete()
                history_obj = obj.history.first()
                history_obj.history_type = "+"
                history_obj.save()
            
            # For plasmid map, detect common features and save as png using snapgene server
            try:
                snapgene_plasmid_map_preview(obj.plasmid_map.path, obj.plasmid_map_png.path, obj.plasmid_map_gbk.path, obj.id, obj.name)
            except:
                messages.warning(request, 'Could not detect common features or save map preview')
    
    def get_readonly_fields(self, request, obj=None):
        '''Override default get_readonly_fields to define user-specific read-only fields
        If a user is not a superuser, lab manager or the user who created a record
        return all fields as read-only
        'created_date_time' and 'last_changed_date_time' fields must always be read-only
        because their set by Django itself'''
        
        if obj:
            if request.user.has_perm('collection_management.change_huplasmid', obj):
                return ['plasmid_map_png', 'plasmid_map_gbk', 'created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by',]
            if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by or obj.created_by.id == 6) or request.user.groups.filter(name='Guest').exists():
                return ['name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 'note', 
                    'reference', 'plasmid_map', 'plasmid_map_png', 'plasmid_map_gbk', 'created_date_time', 'created_approval_by_pi', 'last_changed_date_time',
                    'last_changed_approval_by_pi', 'created_by', 'vector_known_zkbs', 'vector_zkbs','formz_elements']
            else:
                if obj.created_by.id == 6 and not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists()): # Show plasmid_map and note as editable fields, if record belongs to Helle (user id = 6)
                    return ['name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 
                    'reference', 'plasmid_map_png', 'plasmid_map_gbk', 'created_date_time', 'created_approval_by_pi', 'last_changed_date_time',
                    'last_changed_approval_by_pi', 'created_by', 'vector_known_zkbs', 'vector_zkbs','formz_elements']
                else:
                    return ['plasmid_map_png', 'plasmid_map_gbk', 'created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi','created_by',]
        else:
            return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi',]
    
    def add_view(self,request,extra_content=None):
        '''Override default add_view to show only desired fields'''
        
        self.fields = ('name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 'note', 
                'reference', 'plasmid_map',)

        # self.fieldsets = (
        # (None, {
        #     'fields': ('name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 'note', 
        #         'reference', 'plasmid_map',)
        # }),
        # ('Formablatt Z', {
        #     'fields': ('vector_known_zkbs', 'vector_zkbs','formz_elements')
        # }),
        # )

        return super(HuPlasmidPage,self).add_view(request)
    
    def change_view(self,request,object_id,extra_context=None):
        '''Override default change_view to show only desired fields'''

        if object_id:
            obj = collection_management_HuPlasmid.objects.get(pk=object_id)
            if obj:
                if request.user == obj.created_by:
                    self.save_as = True
        
        if '_saveasnew' in request.POST:
            self.fields = ('name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 'note', 
                'reference', 'plasmid_map',)
        else:
            self.fields = ('name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 'note', 
                'reference', 'plasmid_map', 'plasmid_map_png', 'plasmid_map_gbk', 'created_date_time', 'created_approval_by_pi', 'last_changed_date_time',
                'last_changed_approval_by_pi', 'created_by',)

        # if '_saveasnew' in request.POST:
        #     self.fieldsets = (
        #         (None, {
        #             'fields': ('name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 'note', 
        #         'reference', 'plasmid_map',)
        #         }),
        #         ('Formablatt Z', {
        #             'fields': ('vector_known_zkbs', 'vector_zkbs','formz_elements')
        #             }),
        #         )
        # else:
        #     self.fieldsets = (
        #     (None, {
        #         'fields': ('name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 'note', 
        #             'reference', 'plasmid_map', 'plasmid_map_png', 'plasmid_map_gbk', 'created_date_time', 'created_approval_by_pi', 'last_changed_date_time',
        #             'last_changed_approval_by_pi', 'created_by',)
        #     }),
        #     ('Formablatt Z', {
        #         'classes': ('collapse',),
        #         'fields': ('vector_known_zkbs', 'vector_zkbs','formz_elements')
        #     }),
        #     )
        
        return super(HuPlasmidPage,self).change_view(request,object_id,extra_context)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        """Override default changeform_view to hide Save buttons when certain conditions (same as
        those in get_readonly_fields method) are met"""

        extra_context = extra_context or {}
        extra_context['show_submit_line'] = True
        if object_id:
            obj = collection_management_HuPlasmid.objects.get(pk=object_id)
            if obj:
                if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by or obj.created_by.id == 6) or request.user.groups.filter(name='Guest').exists():
                    if not request.user.has_perm('collection_management.change_huplasmid', obj):
                        extra_context['show_submit_line'] = False
        return super(HuPlasmidPage, self).changeform_view(request, object_id, extra_context=extra_context)

    def get_plasmidmap_short_name(self, instance):
        '''This function allows you to define a custom field for the list view to
        be defined in list_display as the name of the function, e.g. in this case
        list_display = ('id', 'name', 'selection', 'get_plasmidmap_short_name','created_by',)'''
        
        if instance.plasmid_map:
            return mark_safe('<a class="image-link" href="{}">png</a> | <a href="{}">dna</a> | <a href="{}">gbk</a>'.format(str(instance.plasmid_map_png.url),str(instance.plasmid_map.url), str(instance.plasmid_map_gbk.url)))
        else:
            return ''
    get_plasmidmap_short_name.short_description = 'Plasmid map'

    class Media:
        css = {
            "all": ('admin/css/vendor/magnific-popup.css',
            )}

    def obj_perms_manage_view(self, request, object_pk):
        """
        Main object Guardian permissions view. 

        Customized to allow only record owner to change permissions
        """
        obj = collection_management_HuPlasmid.objects.get(pk=object_pk)
        
        if obj:
            if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by) or request.user.groups.filter(name='Guest').exists():
                messages.error(request, 'Nice try, you are allowed to change the permissions of your own records only.')
                return HttpResponseRedirect("..")
        return super(HuPlasmidPage,self).obj_perms_manage_view(request, object_pk)

my_admin_site.register(collection_management_HuPlasmid, HuPlasmidPage)

#################################################
#                 OLIGO PAGES                   #
#################################################

from .models import Oligo as collection_management_Oligo

class OligoQLSchema(DjangoQLSchema):
    '''Customize search functionality'''
    
    include = (collection_management_Oligo, User) # Include only the relevant models to be searched
    
    def get_fields(self, model):
        '''Define fields that can be searched'''
        
        if model == collection_management_Oligo:
            return ['id', 'name','sequence', 'us_e', 'gene', 'restriction_site', 'description', 'comment', 'created_by',]
        elif model == User:
            return [SearchFieldOptUsername(), SearchFieldOptLastname()]
        return super(OligoQLSchema, self).get_fields(model)

class OligoExportResource(resources.ModelResource):
    """Defines a custom export resource class for Oligo"""
    
    class Meta:
        model = collection_management_Oligo
        fields = ('id', 'name','sequence', 'us_e', 'gene', 'restriction_site', 'description', 'comment',
        'created_date_time', 'last_changed_date_time', 'created_by__username',)

def export_oligo(modeladmin, request, queryset):
    """Export Oligo as xlsx"""

    export_data = OligoExportResource().export(queryset)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="{}_{}_{}.xlsx'.format(collection_management_Oligo.__name__, time.strftime("%Y%m%d"), time.strftime("%H%M%S"))
    response.write(export_data.xlsx)
    return response
export_oligo.short_description = "Export selected oligos as xlsx"

class OligoPage(DjangoQLSearchMixin, SimpleHistoryWithSummaryAdmin, admin.ModelAdmin, Approval):
    list_display = ('id', 'name','get_oligo_short_sequence', 'restriction_site','created_by', 'approval')
    list_display_links = ('id',)
    list_per_page = 25
    formfield_overrides = {
    models.CharField: {'widget': TextInput(attrs={'size':'93'})},} # Make TextInput fields wider
    djangoql_schema = OligoQLSchema
    actions = [export_oligo]
    save_as = True

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
        
        if obj.pk == None:
            obj.created_by = request.user
            obj.save()
        else:
            if request.user.is_superuser or request.user == collection_management_Oligo.objects.get(pk=obj.pk).created_by or request.user.groups.filter(name='Lab manager').exists():
                obj.last_changed_approval_by_pi = False
                obj.save()
            else:
                raise PermissionDenied
    
    def get_readonly_fields(self, request, obj=None):
        '''Override default get_readonly_fields to define user-specific read-only fields
        If a user is not a superuser, lab manager or the user who created a record
        return all fields as read-only 
        'created_date_time' and 'last_changed_date_time' fields must always be read-only
        because their set by Django itself'''
        
        if obj:
            if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by) or request.user.groups.filter(name='Guest').exists():
                return ['name','sequence', 'us_e', 'gene', 'restriction_site', 'description', 'comment', 'created_date_time',
                'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by',]
            else:
                return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi','created_by']
        else:
            return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi',]
    
    def add_view(self,request,extra_content=None):
        '''Override default add_view to show only desired fields'''
        
        self.fields = ('name','sequence', 'us_e', 'gene', 'restriction_site', 'description', 'comment', )
        return super(OligoPage,self).add_view(request)

    def change_view(self,request,object_id,extra_content=None):
        '''Override default change_view to show only desired fields'''
        

        if object_id:
            obj = collection_management_Oligo.objects.get(pk=object_id)
            if obj:
                if request.user == obj.created_by:
                    self.save_as = True
        
        if '_saveasnew' in request.POST:
            self.fields = ('name','sequence', 'us_e', 'gene', 'restriction_site', 'description', 'comment',
                'created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi', )
        else:
            self.fields = ('name','sequence', 'us_e', 'gene', 'restriction_site', 'description', 'comment',
                'created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by',)
        return super(OligoPage,self).change_view(request,object_id)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        """Override default changeform_view to hide Save buttons when certain conditions (same as
        those in get_readonly_fields method) are met"""

        extra_context = extra_context or {}
        extra_context['show_submit_line'] = True
        if object_id:
            obj = collection_management_Oligo.objects.get(pk=object_id)
            if obj:
                if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by) or request.user.groups.filter(name='Guest').exists():
                    extra_context['show_submit_line'] = False
        return super(OligoPage, self).changeform_view(request, object_id, extra_context=extra_context)

my_admin_site.register(collection_management_Oligo, OligoPage)

#################################################
#            SC. POMBE STRAIN PAGES             #
#################################################

from .models import ScPombeStrain as collection_management_ScPombeStrain

class ScPombeStrainQLSchema(DjangoQLSchema):
    '''Customize search functionality'''
    
    include = (collection_management_ScPombeStrain, User) # Include only the relevant models to be searched

    def get_fields(self, model):
        '''Define fields that can be searched'''
        
        if model == collection_management_ScPombeStrain:
            return ['id', 'box_number', 'parental_strain', 'mating_type', 'auxotrophic_marker', 'name',
                    'phenotype', 'received_from', 'comment', 'created_by',]
        elif model == User:
            return [SearchFieldOptUsername(), SearchFieldOptLastname()]
        return super(ScPombeStrainQLSchema, self).get_fields(model)

class ScPombeStrainExportResource(resources.ModelResource):
    """Defines a custom export resource class for ScPombeStrain"""
    
    class Meta:
        model = collection_management_ScPombeStrain
        fields = ('id', 'box_number', 'parental_strain', 'mating_type', 'auxotrophic_marker', 'name',
        'phenotype', 'received_from', 'comment', 'created_date_time', 'last_changed_date_time', 'created_by__username')

def export_scpombestrain(modeladmin, request, queryset):
    """Export ScPombeStrain as xlsx"""

    export_data = ScPombeStrainExportResource().export(queryset)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="{}_{}_{}.xlsx'.format(collection_management_ScPombeStrain.__name__, time.strftime("%Y%m%d"), time.strftime("%H%M%S"))
    response.write(export_data.xlsx)
    return response
export_scpombestrain.short_description = "Export selected strains as xlsx"

class ScPombeStrainPage(DjangoQLSearchMixin, SimpleHistoryWithSummaryAdmin, admin.ModelAdmin, Approval):
    list_display = ('id', 'name', 'auxotrophic_marker', 'mating_type', 'approval',)
    list_display_links = ('id', )
    list_per_page = 25
    formfield_overrides = {models.CharField: {'widget': TextInput(attrs={'size':'93'})},}
    djangoql_schema = ScPombeStrainQLSchema
    actions = [export_scpombestrain]

    def save_model(self, request, obj, form, change):
        '''Override default save_model to limit a user's ability to save a record
        Superusers and lab managers can change all records
        Regular users can change only their own records
        Guests cannot change any record'''
        
        if obj.pk == None:
            obj.created_by = request.user
            obj.save()
        else:
            if request.user.is_superuser or request.user == collection_management_ScPombeStrain.objects.get(pk=obj.pk).created_by or request.user.groups.filter(name='Lab manager').exists():
                obj.last_changed_approval_by_pi = False
                obj.save()
            else:
                raise PermissionDenied
    
    def get_readonly_fields(self, request, obj=None):
        '''Override default get_readonly_fields to define user-specific read-only fields
        If a user is not a superuser, lab manager or the user who created a record
        return all fields as read-only 
        'created_date_time' and 'last_changed_date_time' fields must always be read-only
        because their set by Django itself'''
        
        if obj:
            if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by) or request.user.groups.filter(name='Guest').exists():
                return ['box_number', 'parental_strain', 'mating_type', 'auxotrophic_marker', 'name',
        'phenotype', 'received_from', 'comment', 'created_date_time', 'created_approval_by_pi',
        'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by',]
            else:
                return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi',]
        else:
            return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi',]

    def add_view(self,request,extra_content=None):
        '''Override default add_view to show only desired fields'''
        
        self.fields = ('box_number', 'parental_strain', 'mating_type', 'auxotrophic_marker', 'name',
        'phenotype', 'received_from', 'comment', )
        return super(ScPombeStrainPage,self).add_view(request)

    def change_view(self,request,object_id,extra_content=None):
        '''Override default change_view to show only desired fields'''
        
        self.fields = ('box_number', 'parental_strain', 'mating_type', 'auxotrophic_marker', 'name',
        'phenotype', 'received_from', 'comment', 'created_date_time', 'created_approval_by_pi',
        'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by',)
        return super(ScPombeStrainPage,self).change_view(request,object_id)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        """Override default changeform_view to hide Save buttons when certain conditions (same as
        those in get_readonly_fields method) are met"""

        extra_context = extra_context or {}
        extra_context['show_submit_line'] = True
        if object_id:
            obj = collection_management_ScPombeStrain.objects.get(pk=object_id)
            if obj:
                if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by) or request.user.groups.filter(name='Guest').exists():
                    extra_context['show_submit_line'] = False
        return super(ScPombeStrainPage, self).changeform_view(request, object_id, extra_context=extra_context)

my_admin_site.register(collection_management_ScPombeStrain, ScPombeStrainPage)

#################################################
#                NZ PLASMID PAGES               #
#################################################

# from .models import NzPlasmid as collection_management_NzPlasmid

# class NzPlasmidQLSchema(DjangoQLSchema):
#     '''Customize search functionality'''
    
#     include = (collection_management_NzPlasmid, User) # Include only the relevant models to be searched

#     def get_fields(self, model):
#         '''Define fields that can be searched'''
        
#         if model == collection_management_NzPlasmid:
#             return ['id', 'name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 'note', 
#                 'reference', 'created_by',]
#         elif model == User:
#             return [SearchFieldOptUsername(), SearchFieldOptLastname()]
#         return super(NzPlasmidQLSchema, self).get_fields(model)

# class NzPlasmidExportResource(resources.ModelResource):
#     """Defines a custom export resource class for NzPlasmid"""
    
#     class Meta:
#         model = collection_management_NzPlasmid
#         fields = ('id', 'name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 'note', 
#                 'reference', 'plasmid_map', 'created_date_time', 'last_changed_date_time', 'created_by__username',)

# def export_nzplasmid(modeladmin, request, queryset):
#     """Export NzPlasmid as xlsx"""

#     export_data = NzPlasmidExportResource().export(queryset)
#     response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
#     response['Content-Disposition'] = 'attachment; filename="{}_{}_{}.xlsx'.format(collection_management_NzPlasmid.__name__, time.strftime("%Y%m%d"), time.strftime("%H%M%S"))
#     response.write(export_data.xlsx)
#     return response
# export_nzplasmid.short_description = "Export selected plasmids as xlsx"

# class NzPlasmidPage(DjangoQLSearchMixin, SimpleHistoryWithSummaryAdmin, CustomGuardedModelAdmin, Approval):
#     list_display = ('id', 'name', 'selection', 'get_plasmidmap_short_name','created_by', 'approval')
#     list_display_links = ('id', )
#     list_per_page = 25
#     formfield_overrides = {models.CharField: {'widget': TextInput(attrs={'size':'93'})},}
#     djangoql_schema = NzPlasmidQLSchema
#     actions = [export_nzplasmid]
    
#     def save_model(self, request, obj, form, change):
#         '''Override default save_model to limit a user's ability to save a record
#         Superusers and lab managers can change all records
#         Regular users can change only their own records
#         Guests cannot change any record.
#         It also renames a plasmid map to pNZ{obj.id}_{date_created}_{time_created}.ext
#         and whenever possible creates a plasmid map preview with snapegene server'''

#         rename_and_preview = False
#         new_obj = False

#         if obj.pk == None:
#             obj.created_by = request.user
#             if obj.plasmid_map:
#                 rename_and_preview = True
#                 new_obj = True
#             obj.save()
#         else:
#             old_obj = collection_management_NzPlasmid.objects.get(pk=obj.pk)
#             if request.user.is_superuser or request.user == old_obj.created_by or request.user.groups.filter(name='Lab manager').exists():
#                 obj.last_changed_approval_by_pi = False
#                 if obj.plasmid_map and obj.plasmid_map != old_obj.plasmid_map:
#                     rename_and_preview = True
#                     obj.save_without_historical_record()
#                 else:
#                     obj.save()
#             else:
#                 raise PermissionDenied
        
#         # Rename plasmid map
#         if rename_and_preview:
#             plasmid_map_dir_path = os.path.join(MEDIA_ROOT, 'collection_management/nzplasmid/')
#             old_file_name_abs_path = os.path.join(MEDIA_ROOT, obj.plasmid_map.name)
#             old_file_name, ext = os.path.splitext(os.path.basename(old_file_name_abs_path)) 
#             new_file_name = os.path.join(
#                 'collection_management/nzplasmid/', 
#                 "pNZ{}_{}_{}{}".format(obj.id, time.strftime("%Y%m%d"), time.strftime("%H%M%S"), ext.lower()))
#             new_file_name_abs_path = os.path.join(MEDIA_ROOT, new_file_name)
            
#             if not os.path.exists(plasmid_map_dir_path):
#                 os.makedirs(plasmid_map_dir_path) 
            
#             os.rename(
#                 old_file_name_abs_path, 
#                 new_file_name_abs_path)
            
#             obj.plasmid_map.name = new_file_name
#             obj.save()

#             # For new records, delete first history record, which contains the unformatted plasmid_map name, and change 
#             # the newer history record's history_type from changed (~) to created (+). This gets rid of a duplicate
#             # history record created when automatically generating a plasmid_map name
#             if new_obj:
#                 obj.history.last().delete()
#                 history_obj = obj.history.first()
#                 history_obj.history_type = "+"
#                 history_obj.save()
            
#             # For plasmid map, detect common features and save as png using snapgene server
#             try:
#                 snapgene_plasmid_map_preview(new_file_name_abs_path, "pNZ", obj.id, obj.name)
#             except:
#                 messages.warning(request, 'Could not detect common features or save map preview')
                
#     def get_readonly_fields(self, request, obj=None):
#         '''Override default get_readonly_fields to define user-specific read-only fields
#         If a user is not a superuser, lab manager or the user who created a record
#         return all fields as read-only 
#         'created_date_time' and 'last_changed_date_time' fields must always be read-only
#         because their set by Django itself'''
        
#         if obj:
#             if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by) or request.user.groups.filter(name='Guest').exists():
#                 if request.user.has_perm('collection_management.change_nzplasmid', obj):
#                     return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by']
#                 else:
#                     return ['name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 'note', 
#                     'reference', 'plasmid_map', 'created_date_time', 'created_approval_by_pi', 'last_changed_date_time',
#                     'last_changed_approval_by_pi', 'created_by',]
#             else:
#                 return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by']
#         else:
#             return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi',]
    
#     def add_view(self,request,extra_content=None):
#         '''Override default add_view to show only desired fields'''
        
#         self.fields = ('name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 'note', 
#                 'reference', 'plasmid_map',)
#         return super(NzPlasmidPage,self).add_view(request)

#     def change_view(self,request,object_id,extra_content=None):
#         '''Override default change_view to show only desired fields'''
        
#         self.fields = ('name', 'other_name', 'parent_vector', 'selection', 'us_e', 'construction_feature', 'received_from', 'note', 
#                 'reference', 'plasmid_map', 'created_date_time', 'created_approval_by_pi', 'last_changed_date_time',
#                 'last_changed_approval_by_pi', 'created_by',)
#         return super(NzPlasmidPage,self).change_view(request,object_id)

#     def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
#         """Override default changeform_view to hide Save buttons when certain conditions (same as
#         those in get_readonly_fields method) are met"""

#         extra_context = extra_context or {}
#         extra_context['show_submit_line'] = True
#         if object_id:
#             obj = collection_management_NzPlasmid.objects.get(pk=object_id)
#             if obj:
#                 if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by) or request.user.groups.filter(name='Guest').exists():
#                     if not request.user.has_perm('collection_management.change_nzplasmid', obj):
#                         extra_context['show_submit_line'] = False
#         return super(NzPlasmidPage, self).changeform_view(request, object_id, extra_context=extra_context)

#     def get_plasmidmap_short_name(self, instance):
#         '''This function allows you to define a custom field for the list view to
#         be defined in list_display as the name of the function, e.g. in this case
#         list_display = ('id', 'name', 'selection', 'get_plasmidmap_short_name','created_by',)'''
#         if instance.plasmid_map:
#             return mark_safe('<a class="image-link" href="{0}">View</a> | <a href="{1}">Download</a>'.format(str(instance.plasmid_map.url.replace("collection_management", "plasmid_map_png").replace(".dna", ".png")),str(instance.plasmid_map.url)))
#         else:
#             return ''
#     get_plasmidmap_short_name.short_description = 'Plasmid map'

#     class Media:
#         css = {
#             "all": ('admin/css/vendor/magnific-popup.css',
#             )}

#     def obj_perms_manage_view(self, request, object_pk):
#         """
#         Main object Guardian permissions view. 

#         Customized to allow only record owner to change permissions
#         """
#         obj = collection_management_NzPlasmid.objects.get(pk=object_pk)
        
#         if obj:
#             if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by) or request.user.groups.filter(name='Guest').exists():
#                 messages.error(request, 'Nice try, you are allowed to change the permissions of your own records only.')
#                 return HttpResponseRedirect("..")
#         return super(NzPlasmidPage,self).obj_perms_manage_view(request, object_pk)

# my_admin_site.register(collection_management_NzPlasmid, NzPlasmidPage)

#################################################
#              E. COLI STRAIN PAGES             #
#################################################

from .models import EColiStrain as collection_management_EColiStrain

class EColiStrainQLSchema(DjangoQLSchema):
    '''Customize search functionality'''
    
    include = (collection_management_EColiStrain, User) # Include only the relevant models to be searched

    def get_fields(self, model):
        '''Define fields that can be searched'''
        
        if model == collection_management_EColiStrain:
            return ['id', 'name', 'resistance', 'genotype', 'supplier', 'us_e', 'purpose', 'note', 'created_by',]
        elif model == User:
            return [SearchFieldOptUsername(), SearchFieldOptLastname()]
        return super(EColiStrainQLSchema, self).get_fields(model)

class EColiStrainExportResource(resources.ModelResource):
    """Defines a custom export resource class for EColiStrain"""
    
    class Meta:
        model = collection_management_EColiStrain
        fields = ('id' ,'name', 'resistance', 'genotype', 'supplier', 'us_e', 'purpose', 'note',
                'created_date_time', 'last_changed_date_time', 'created_by__username',)

def export_ecolistrain(modeladmin, request, queryset):
    """Export EColiStrain as xlsx"""

    export_data = EColiStrainExportResource().export(queryset)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="{}_{}_{}.xlsx'.format(collection_management_EColiStrain.__name__, time.strftime("%Y%m%d"), time.strftime("%H%M%S"))
    response.write(export_data.xlsx)
    return response
export_ecolistrain.short_description = "Export selected strains as xlsx"

class EColiStrainPage(DjangoQLSearchMixin, SimpleHistoryWithSummaryAdmin, admin.ModelAdmin, Approval):
    list_display = ('id', 'name', 'resistance', 'us_e','purpose', 'approval')
    list_display_links = ('id', )
    list_per_page = 25
    formfield_overrides = {models.CharField: {'widget': TextInput(attrs={'size':'93'})},}
    djangoql_schema = EColiStrainQLSchema
    actions = [export_ecolistrain]
    
    def save_model(self, request, obj, form, change):
        '''Override default save_model to limit a user's ability to save a record
        Superusers and lab managers can change all records
        Regular users can change only their own records
        Guests cannot change any record'''

        if obj.pk == None:
            obj.created_by = request.user
            obj.save()
        else:
            if request.user.is_superuser or request.user == collection_management_EColiStrain.objects.get(pk=obj.pk).created_by or request.user.groups.filter(name='Lab manager').exists():
                obj.last_changed_approval_by_pi = False
                obj.save()
            else:
                raise PermissionDenied
                
    def get_readonly_fields(self, request, obj=None):
        '''Override default get_readonly_fields to define user-specific read-only fields
        If a user is not a superuser, lab manager or the user who created a record
        return all fields as read-only 
        'created_date_time' and 'last_changed_date_time' fields must always be read-only
        because their set by Django itself'''

        if obj:
            if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by) or request.user.groups.filter(name='Guest').exists():
                return ['name', 'resistance', 'genotype', 'supplier', 'us_e', 'purpose', 'note',
                'created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by',]
            else:
                return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi',]
        else:
            return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi',]
    
    def add_view(self,request,extra_content=None):
        '''Override default add_view to show only desired fields'''

        self.fields = ('name', 'resistance', 'genotype', 'supplier', 'us_e', 'purpose', 'note',)
        return super(EColiStrainPage,self).add_view(request)

    def change_view(self,request,object_id,extra_content=None):
        '''Override default change_view to show only desired fields'''

        self.fields = ('name', 'resistance', 'genotype', 'supplier', 'us_e', 'purpose', 'note',
                'created_date_time', 'created_approval_by_pi', 'last_changed_date_time',
                'last_changed_approval_by_pi', 'created_by',)
        return super(EColiStrainPage,self).change_view(request,object_id)
    
    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        """Override default changeform_view to hide Save buttons when certain conditions (same as
        those in get_readonly_fields method) are met"""

        extra_context = extra_context or {}
        extra_context['show_submit_line'] = True
        if object_id:
            obj = collection_management_EColiStrain.objects.get(pk=object_id)
            if obj:
                if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by) or request.user.groups.filter(name='Guest').exists():
                    extra_context['show_submit_line'] = False
        return super(EColiStrainPage, self).changeform_view(request, object_id, extra_context=extra_context)

my_admin_site.register(collection_management_EColiStrain, EColiStrainPage)

#################################################
#           MAMMALIAN LINE DOC                  #
#################################################

from .models import MammalianLineDoc as collection_management_MammalianLineDoc
from .models import MammalianLine as collection_management_MammalianLine

class MammalianLinePageDoc(admin.ModelAdmin):
    list_display = ('id','name',)
    list_display_links = ('id','name', )
    list_per_page = 25
    ordering = ['id']

    def has_module_permission(self, request):
        '''Hide module from Admin'''
        return False

    def get_readonly_fields(self, request, obj=None):
        '''Override default get_readonly_fields to define user-specific read-only fields
        If a user is not a superuser, lab manager or the user who created a record
        return all fields as read-only 
        'created_date_time' and 'last_changed_date_time' fields must always be read-only
        because their set by Django itself'''

        if obj:
            return ['name', 'typ_e', 'date_of_test', 'mammalian_line', 'created_date_time',]
    
    def add_view(self,request,extra_content=None):
        '''Override default add_view to show only desired fields'''

        self.fields = (['name', 'typ_e', 'mammalian_line', 'comment', 'date_of_test'])
        return super(MammalianLinePageDoc,self).add_view(request)

    def change_view(self,request,object_id,extra_content=None):
        '''Override default change_view to show only desired fields'''

        self.fields = (['name', 'typ_e', 'date_of_test', 'mammalian_line', 'comment', 'created_date_time',])
        return super(MammalianLinePageDoc,self).change_view(request,object_id)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_submit_line'] = True
        if object_id:
            extra_context['show_submit_line'] = False
        return super(MammalianLinePageDoc, self).changeform_view(request, object_id, extra_context=extra_context)

my_admin_site.register(collection_management_MammalianLineDoc, MammalianLinePageDoc)

class MammalianLineDocInline(admin.TabularInline):
    """Inline to view existing mammalian line documents"""

    model = collection_management_MammalianLineDoc
    verbose_name_plural = "Existing docs"
    extra = 0
    fields = ['typ_e', 'date_of_test', 'get_doc_short_name', 'comment']
    readonly_fields = ['get_doc_short_name', 'typ_e', 'date_of_test']

    def has_add_permission(self, request):
        return False
    
    def get_doc_short_name(self, instance):
        '''This function allows you to define a custom field for the list view to
        be defined in list_display as the name of the function, e.g. in this case
        list_display = ('id', 'name', 'selection', 'get_plasmidmap_short_name','created_by',)'''
        if instance.name:
            return mark_safe('<a href="{}">View</a>'.format(str(instance.name.url)))
        else:
            return ''
    get_doc_short_name.short_description = 'Document'

class AddMammalianLineDocInline(admin.TabularInline):
    """Inline to add new mammalian line documents"""
    
    model = collection_management_MammalianLineDoc
    verbose_name_plural = "New docs"
    extra = 0
    fields = ['typ_e', 'date_of_test', 'name','comment']

    def has_change_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        '''Override default get_readonly_fields to define user-specific read-only fields
        If a user is not a superuser, lab manager or the user who created a record
        return all fields as read-only'''

        if obj:
            if request.user.groups.filter(name='Guest').exists():
                return ['typ_e', 'date_of_test', 'name', 'comment']
            else:
                return []
        else:
            return []

#################################################
#          MAMMALIAN CELL LINE PAGES            #
#################################################

class MammalianLineQLSchema(DjangoQLSchema):
    '''Customize search functionality'''
    
    include = (collection_management_MammalianLine, User) # Include only the relevant models to be searched

    def get_fields(self, model):
        '''Define fields that can be searched'''
        
        if model == collection_management_MammalianLine:
            return ['id', 'name', 'box_name', 'alternative_name', 'parental_line', 'organism', 'cell_type_tissue', 'culture_type', 
            'growth_condition','freezing_medium', 'received_from', 'description_comment', 'created_by',]
        elif model == User:
            return [SearchFieldOptUsername(), SearchFieldOptLastname()]
        return super(MammalianLineQLSchema, self).get_fields(model)

class MammalianLineExportResource(resources.ModelResource):
    """Defines a custom export resource class for MammalianLine"""
    
    class Meta:
        model = collection_management_MammalianLine
        fields = ('id','name', 'box_name', 'alternative_name', 'parental_line', 'organism', 'cell_type_tissue', 
                'culture_type', 'growth_condition', 'freezing_medium', 'received_from', 'description_comment', 
                'created_date_time', 'last_changed_date_time', 'created_by__username',)

def export_mammalianline(modeladmin, request, queryset):
    """Export MammalianLine as xlsx"""

    export_data = MammalianLineExportResource().export(queryset)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="{}_{}_{}.xlsx'.format(collection_management_MammalianLine.__name__, time.strftime("%Y%m%d"), time.strftime("%H%M%S"))
    response.write(export_data.xlsx)
    return response
export_mammalianline.short_description = "Export selected cell lines as xlsx"

class MammalianLinePage(DjangoQLSearchMixin, SimpleHistoryWithSummaryAdmin, CustomGuardedModelAdmin, Approval):
    list_display = ('id', 'name', 'box_name', 'created_by', 'approval')
    list_display_links = ('id', )
    list_per_page = 25
    formfield_overrides = {models.CharField: {'widget': TextInput(attrs={'size':'93'})},}
    djangoql_schema = MammalianLineQLSchema
    inlines = [MammalianLineDocInline, AddMammalianLineDocInline]
    actions = [export_mammalianline]

    search_fields = ['id', 'name']
    autocomplete_fields = ['parental_line']

    def save_model(self, request, obj, form, change):
        '''Override default save_model to limit a user's ability to save a record
        Superusers and lab managers can change all records
        Regular users can change only their own records
        Guests cannot change any record'''

        if obj.pk == None:
            obj.created_by = request.user
            obj.save()
        else:
            if not request.user.groups.filter(name='Guest').exists():
                obj.last_changed_approval_by_pi = False
                obj.save()
            else:
                raise PermissionDenied
    
    def get_readonly_fields(self, request, obj=None):
        '''Override default get_readonly_fields to define user-specific read-only fields
        If a user is not a superuser, lab manager or the user who created a record
        return all fields as read-only 
        'created_date_time' and 'last_changed_date_time' fields must always be read-only
        because their set by Django itself'''

        if obj:
            if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by) or request.user.groups.filter(name='Guest').exists():
                if request.user.has_perm('collection_management.change_mammalianline', obj):
                    return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by']
                else:
                    return ['name', 'box_name', 'alternative_name', 'organism', 'cell_type_tissue', 'culture_type', 'growth_condition',
                    'freezing_medium', 'received_from', 'description_comment', 'created_date_time', 'created_approval_by_pi',
                    'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by',]
            else:
                return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by']
        else:
            return ['created_date_time', 'created_approval_by_pi', 'last_changed_date_time', 'last_changed_approval_by_pi',]

    def get_form(self, request, obj=None, **kwargs):
        """
        Modify the default factory to change form fields based on the request/object.
        """
        default_factory = super(MammalianLinePage, self).get_form(request, obj=obj, **kwargs)

        def factory(*args, **_kwargs):
            form = default_factory(*args, **_kwargs)
            return self.modify_form(form, request, obj, **_kwargs)

        return factory

    @staticmethod
    def modify_form(form, request, obj, **kwargs):
        """
        Edit 'parental_line' field
        """
        if obj:
            # try:
            #     form.fields['parental_line'].help_text = mark_safe( '<a target="_blank" href="{}">View</a>'.format(reverse("admin:{}_{}_change".format(obj._meta.app_label, obj._meta.model_name), args=(obj.parental_line.id,))))
            # except:
            #     pass
            if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by) or request.user.groups.filter(name='Guest').exists():
                if not request.user.has_perm('collection_management.change_mammalianline', obj):
                    form.fields['parental_line'].disabled = True
        return form

    def add_view(self,request,extra_content=None):
        '''Override default add_view to show only desired fields'''

        self.fields = ('name', 'box_name', 'alternative_name', 'parental_line', 'organism', 'cell_type_tissue', 'culture_type', 'growth_condition',
                'freezing_medium', 'received_from', 'description_comment',)
        return super(MammalianLinePage,self).add_view(request)

    def change_view(self,request,object_id,extra_content=None):
        '''Override default change_view to show only desired fields'''

        self.fields = ('name', 'box_name', 'alternative_name', 'parental_line', 'organism', 'cell_type_tissue', 'culture_type', 'growth_condition',
                'freezing_medium', 'received_from', 'description_comment', 'created_date_time', 'created_approval_by_pi',
                'last_changed_date_time', 'last_changed_approval_by_pi', 'created_by',)
        return super(MammalianLinePage,self).change_view(request,object_id)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        """Override default changeform_view to hide Save buttons when certain conditions (same as
        those in get_readonly_fields method) are met"""

        extra_context = extra_context or {}
        extra_context['show_submit_line'] = True
        if object_id:
            obj = collection_management_MammalianLine.objects.get(pk=object_id)
            if obj:
                if request.user.groups.filter(name='Guest').exists():
                    extra_context['show_submit_line'] = False
        return super(MammalianLinePage, self).changeform_view(request, object_id, extra_context=extra_context)

    def get_formsets_with_inlines(self, request, obj=None):
        """Remove AddMammalianLineDocInline from add/change form if user who
        created a MammalianCellLine object is not the request user a lab manager
        or a superuser"""
        
        if obj:
            for inline in self.get_inline_instances(request, obj):
                if inline.verbose_name_plural == 'Existing docs':
                    yield inline.get_formset(request, obj), inline
                else:
                    if not request.user.groups.filter(name='Guest').exists():
                        yield inline.get_formset(request, obj), inline
        else:
            for inline in self.get_inline_instances(request, obj):
                if inline.verbose_name_plural == 'Existing docs':
                    continue
                else:
                    yield inline.get_formset(request, obj), inline
    
    def obj_perms_manage_view(self, request, object_pk):
        """
        Main object Guardian permissions view. 

        Customized to allow only record owner to change permissions
        """
        obj = collection_management_MammalianLine.objects.get(pk=object_pk)
        
        if obj:
            if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user == obj.created_by) or request.user.groups.filter(name='Guest').exists():
                messages.error(request, 'Nice try, you are allowed to change the permissions of your own records only.')
                return HttpResponseRedirect("..")
        return super(MammalianLinePage,self).obj_perms_manage_view(request, object_pk)

my_admin_site.register(collection_management_MammalianLine, MammalianLinePage)

#################################################
#                ANTIBODY PAGES                 #
#################################################

from .models import Antibody as collection_management_Antibody

class AntibodyQLSchema(DjangoQLSchema):
    '''Customize search functionality'''
    
    include = (collection_management_Antibody, User) # Include only the relevant models to be searched

    def get_fields(self, model):
        '''Define fields that can be searched'''
        
        if model == collection_management_Antibody:
            return ['id', 'name', 'species_isotype', 'clone', 'received_from', 'catalogue_number', 'info_sheet',
                'l_ocation', 'a_pplication', 'description_comment','info_sheet', 'created_by', ]
        elif model == User:
            return [SearchFieldOptUsername(), SearchFieldOptLastname()]
        return super(AntibodyQLSchema, self).get_fields(model)

class AntibodyExportResource(resources.ModelResource):
    """Defines a custom export resource class for Antibody"""
    
    class Meta:
        model = collection_management_Antibody
        fields = ('id', 'name', 'species_isotype', 'clone', 'received_from', 'catalogue_number', 'l_ocation', 'a_pplication',
                'description_comment', 'info_sheet','created_date_time','last_changed_date_time',)

def export_antibody(modeladmin, request, queryset):
    """Export Antibody as xlsx"""

    export_data = AntibodyExportResource().export(queryset)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="{}_{}_{}.xlsx'.format(collection_management_Antibody.__name__, time.strftime("%Y%m%d"), time.strftime("%H%M%S"))
    response.write(export_data.xlsx)
    return response
export_antibody.short_description = "Export selected antibodies as xlsx"

class AntibodyPage(DjangoQLSearchMixin, SimpleHistoryWithSummaryAdmin, admin.ModelAdmin):
    list_display = ('id', 'name', 'catalogue_number', 'received_from', 'species_isotype', 'clone', 'l_ocation', 'get_sheet_short_name')
    list_display_links = ('id', )
    list_per_page = 25
    formfield_overrides = {models.CharField: {'widget': TextInput(attrs={'size':'93'})},}
    djangoql_schema = AntibodyQLSchema
    actions = [export_antibody]
    
    def save_model(self, request, obj, form, change):
        '''Override default save_model to limit a user's ability to save a record
        Superusers and lab managers can change all records
        Regular users can change only their own records
        Guests cannot change any record
        Also automatically renames info_sheet
        '''

        rename_doc = False
        new_obj = False

        if obj.pk == None:
            obj.created_by = request.user
            if obj.info_sheet:
                rename_doc = True
                new_obj = True
            obj.save()
        else:
            if request.user.groups.filter(name='Guest').exists():
                raise PermissionDenied
            old_obj = collection_management_Antibody.objects.get(pk=obj.pk)
            if obj.info_sheet and obj.info_sheet != old_obj.info_sheet:
                rename_doc = True
                obj.save_without_historical_record()
            else:
                obj.save()

        # Rename info_sheet
        if rename_doc:
            doc_dir_path = os.path.join(MEDIA_ROOT, 'collection_management/antibody/')
            old_file_name_abs_path = os.path.join(MEDIA_ROOT, obj.info_sheet.name)
            old_file_name, ext = os.path.splitext(os.path.basename(old_file_name_abs_path)) 
            new_file_name = os.path.join(
                'collection_management/antibody/',
                "abHU{}_f{}".format(obj.id, ext.lower()))
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
        
    def get_readonly_fields(self, request, obj=None):
        '''Override default get_readonly_fields to define user-specific read-only fields
        If a user is not a superuser, lab manager or the user who created a record
        return all fields as read-only 
        'created_date_time' and 'last_changed_date_time' fields must always be read-only
        because their set by Django itself'''

        if obj:
            if request.user.groups.filter(name='Guest').exists():
                return ['name', 'species_isotype', 'clone', 'received_from', 'catalogue_number', 'info_sheet',
                'l_ocation', 'a_pplication', 'description_comment','info_sheet', 'created_by', 'created_date_time',
                'last_changed_date_time',]
            else:
                return ['created_date_time', 'last_changed_date_time',]
        else:
            return ['created_date_time', 'last_changed_date_time',]
    
    def add_view(self,request,extra_content=None):
        '''Override default add_view to show only desired fields'''

        self.fields = ('name', 'species_isotype', 'clone', 'received_from', 'catalogue_number', 'l_ocation', 'a_pplication',
                'description_comment', 'info_sheet', )
        return super(AntibodyPage,self).add_view(request)
    
    def change_view(self,request,object_id,extra_content=None):
        '''Override default change_view to show only desired fields'''

        self.fields = ('name', 'species_isotype', 'clone', 'received_from', 'catalogue_number', 'l_ocation', 'a_pplication',
                'description_comment', 'info_sheet','created_date_time','last_changed_date_time', )
        return super(AntibodyPage,self).change_view(request,object_id)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        """Override default changeform_view to hide Save buttons when certain conditions (same as
        those in get_readonly_fields method) are met"""

        extra_context = extra_context or {}
        extra_context['show_submit_line'] = True
        if object_id:
            obj = collection_management_Antibody.objects.get(pk=object_id)
            if obj:
                if request.user.groups.filter(name='Guest').exists():
                    extra_context['show_submit_line'] = False
        return super(AntibodyPage, self).changeform_view(request, object_id, extra_context=extra_context)

    def get_sheet_short_name(self, instance):
        '''Create custom column for information sheet
        It formats a html element a for the information sheet
        such that the text shown for a link is always View'''

        if instance.info_sheet:
            return mark_safe('<a href="{}">View</a>'.format(str(instance.info_sheet.url)))
        else:
            return ''
    get_sheet_short_name.short_description = 'Info Sheet'

my_admin_site.register(collection_management_Antibody, AntibodyPage)

#################################################
#             ORDER MANAGEMENT PAGES            #
#################################################

from order_management.models import CostUnit as order_management_CostUnit
from order_management.models import Location as order_management_Location
from order_management.models import Order as order_management_Order
from order_management.models import OrderExtraDoc as order_management_OrderExtraDoc
from order_management.models import MsdsForm as order_management_MsdsForm

from order_management.admin import SearchFieldOptLocation, SearchFieldOptCostUnit, SearchFieldOptSupplier, SearchFieldOptPartDescription, OrderQLSchema
from order_management.admin import OrderExtraDocInline
from order_management.admin import AddOrderExtraDocInline
from order_management.admin import CostUnitPage as order_management_CostUnitPage
from order_management.admin import LocationPage as order_management_LocationPage
from order_management.admin import OrderPage as order_management_OrderPage
from order_management.admin import MsdsFormPage as order_management_MsdsFormPage
from order_management.admin import OrderExtraDocPage as order_management_OrderExtraDocPage

my_admin_site.register(order_management_Order, order_management_OrderPage)
my_admin_site.register(order_management_CostUnit, order_management_CostUnitPage)
my_admin_site.register(order_management_Location, order_management_LocationPage)
my_admin_site.register(order_management_MsdsForm, order_management_MsdsFormPage)
my_admin_site.register(order_management_OrderExtraDoc, order_management_OrderExtraDocPage)

#################################################
#            CUSTOM USER/GROUP PAGES            #
#################################################

my_admin_site.register(Group, GroupAdmin)
my_admin_site.register(User, UserAdmin)

from user_management.models import LabUser as user_management_LabUser

from user_management.admin import LabUserAdmin as user_management_LabUserAdmin

my_admin_site.unregister(User)
my_admin_site.register(User, user_management_LabUserAdmin)

#################################################
#               BACKGROUND TASKS                #
#################################################

from background_task.models import Task
from background_task.models_completed import CompletedTask

from background_task.admin import TaskAdmin
from background_task.admin import CompletedTaskAdmin

my_admin_site.register(Task, TaskAdmin)
my_admin_site.register(CompletedTask, CompletedTaskAdmin)

#################################################
#                  FORMBLATT Z                  #
#################################################

from formz.models import NucleicAcidPurity as formz_NucleicAcidPurity
from formz.models import NucleicAcidRisk as formz_NucleicAcidRisk
from formz.models import GenTechMethod as formz_GenTechMethod
from formz.models import FormZProject
from formz.models import FormZBaseElement
from formz.models import FormZHeader

from formz.admin import NucleicAcidPurityPage as formz_NucleicAcidPurityPage
from formz.admin import NucleicAcidRiskPage as formz_NucleicAcidRiskPage
from formz.admin import GenTechMethodPage as formz_GenTechMethodPage
from formz.admin import FormZProjectPage
from formz.admin import FormZBaseElementPage
from formz.admin import FormZHeaderPage

my_admin_site.register(formz_NucleicAcidPurity, formz_NucleicAcidPurityPage)
my_admin_site.register(formz_NucleicAcidRisk, formz_NucleicAcidRiskPage)
my_admin_site.register(formz_GenTechMethod, formz_GenTechMethodPage)
my_admin_site.register(FormZProject, FormZProjectPage)
my_admin_site.register(FormZBaseElement, FormZBaseElementPage)
my_admin_site.register(FormZHeader, FormZHeaderPage)