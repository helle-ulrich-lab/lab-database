#################################################
#    DJANGO 'CORE' FUNCTIONALITIES IMPORTS      #
#################################################

from django.contrib import admin
from django.apps import apps
from django.utils.text import capfirst
from django.http import HttpResponseRedirect
from django.contrib.auth.models import Group, User
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import force_text
from django.shortcuts import render

#################################################
#        ADDED FUNCTIONALITIES IMPORTS          #
#################################################

# Import/Export functionalities from django-import-export
from import_export import resources

# Http stuff
import http.cookiejar
import urllib.request, urllib.parse

#################################################
#                OTHER IMPORTS                  #
#################################################

import datetime
from snapgene.pyclasses.client import Client
from snapgene.pyclasses.config import Config
import zmq
import os
import time

from formz.models import FormZBaseElement
from formz.models import FormZProject

from django_project.private_settings import SITE_TITLE

from .models import GeneralSetting

#################################################
#                CUSTOM CLASSES                 #
#################################################

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

#################################################
#               CUSTOM ADMIN SITE               #
#################################################

class MyAdminSite(admin.AdminSite):
    '''Create a custom admin site called MyAdminSite'''
    
    # Text to put at the end of each page's <title>.
    site_title = SITE_TITLE

    # Text to put in each page's <h1>.
    site_header = SITE_TITLE

    # Text to put at the top of the admin index page.
    index_title = 'Home'

    # URL for the "View site" link at the top of each admin page.
    site_url = '/'

    def get_urls(self):
        
        from django.conf.urls import url
        from django.urls import path
        
        urls = super(MyAdminSite, self).get_urls()
        # Note that custom urls get pushed to the list (not appended)
        # This doesn't work with urls += ...
        urls = [
            url(r'^order_management/my_orders_redirect$', self.admin_view(self.my_orders_redirect)),
            url(r'uploads/(?P<url_path>.*)$', self.admin_view(self.uploads)),
            url(r'^150freezer/$', self.freezer150),
            path('<path:object_id>/formz/', self.admin_view(self.formz))
        ] + urls
        return urls

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
            
            # Create HttpResponse and add Content Type and, if present, Encoding
            response = HttpResponse()
            mimetype, encoding = mimetypes.guess_type(url_path)
            mimetype = mimetype if mimetype else 'application/octet-stream'
            response["Content-Type"] = mimetype
            if encoding:
                response["Content-Encoding"] = encoding
            
            # Get app and model names
            try:
                #app_name, model_name, file_type, file_name = url_path.split('/')
                url_path_split = url_path.split('/')
                app_name = url_path_split[0]
                model_name = url_path_split[1]

                # Generate name for download file
                if app_name == 'collection_management':

                    # Get object 
                    file_name, file_ext = os.path.splitext(url_path_split[-1]) 
                    file_prefix = file_name.split('_')[0]
                    if model_name == 'mammalianlinedoc':
                        obj_id = int(file_name.split('_')[-1])
                    else:
                        obj_id = int(re.findall('\d+(?=_)', file_name)[0])
                    obj = apps.get_model(app_name, model_name).objects.get(id=obj_id)  

                    if model_name == 'mammalianlinedoc':
                        obj_name = "{} - {} Doc# {}".format(obj.mammalian_line.name, obj.typ_e.title(), obj.id)
                    else:
                        obj_name = obj.name

                    download_file_name = "{} - {}{}".format(file_prefix, obj_name, file_ext).replace(',','')
                else:
                    download_file_name = os.path.basename(url_path)
            
            except:
                download_file_name = os.path.basename(url_path)

            # Set content disposition based on file type
            if 'pdf' in mimetype.lower():
                response["Content-Disposition"] = 'inline; filename="{}"'.format(download_file_name)
            elif 'png' in mimetype.lower():
                response["Content-Disposition"] = ""
            else:
                response["Content-Disposition"] = 'attachment; filename="{}"'.format(download_file_name)
            
            response['X-Accel-Redirect'] = "/secret/{url_path}".format(url_path=url_path)
            return response
            
        else:
            raise Http404

    def freezer150(self, request):
        """ View to show the temperature of the -150° C freezer """

        from bs4 import BeautifulSoup
        from django.shortcuts import render

        general_setting = GeneralSetting.objects.all().first()

        # Log on to the Saveris website, browse to page that shows T and read response
        html = DataLoggerWebsiteLogin(general_setting.saveris_username,
                                      general_setting.saveris_password).\
                                      opener.open('https://www.saveris.net/MeasuringPts').read()

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
        'title':"-150° C Freezer", 
        'data':[date_time, T]
        }
        
        return render(request, 'admin/freezer150.html', context)

    def formz(self, request, *args, **kwargs):

        from formz.models import FormZStorageLocation
        from formz.models import FormZHeader
        
        app_label, model_name, obj_id = kwargs['object_id'].split('/')
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

        if model_name == 'mammalianline':
            storage_location.species_name = obj.organism
            obj.s2_plasmids = obj.mammalianlineepisomalplasmid_set.all().filter(s2_work_episomal_plasmid=True).distinct().order_by('id')
            transfected = True
        else:
            obj.s2_plasmids = None
            transfected = False

        context = {
        'title': 'FormZ: {}'.format(obj),
        'module_name': capfirst(force_text(opts.verbose_name_plural)),
        'site_header': self.site_header,
        'has_permission': self.has_permission(request),
        'app_label': app_label,
        'opts': opts,
        'site_url': self.site_url, 
        'object': obj,
        'storage_location': storage_location,
        'formz_header': formz_header,
        'transfected': transfected}

        return render(request, 'admin/formz.html', context)

# Instantiate custom admin site 
my_admin_site = MyAdminSite()

# Disable delete selected action
my_admin_site.disable_action('delete_selected')

#################################################
#              GENERAL SETTINGS                 #
#################################################

class GeneralSettingPage(admin.ModelAdmin):
    
    list_display = ('site_title', )
    list_display_links = ('site_title', )
    list_per_page = 25

    def site_title(self, instance):
        return SITE_TITLE
    site_title.short_description = 'Site title'

    def add_view(self,request,extra_content=None):
        
        # Override default add_view to prevent addition of new records, one is enough!
        raise PermissionDenied

my_admin_site.register(GeneralSetting, GeneralSettingPage)

#################################################
#          COLLECTION MANAGEMENT PAGES          #
#################################################

from collection_management.models import SaCerevisiaeStrain
from collection_management.models import Plasmid
from collection_management.models import Oligo
from collection_management.models import ScPombeStrain
from collection_management.models import EColiStrain
from collection_management.models import MammalianLine
from collection_management.models import MammalianLineDoc
from collection_management.models import Antibody

from collection_management.admin import SaCerevisiaeStrainPage
from collection_management.admin import PlasmidPage
from collection_management.admin import OligoPage
from collection_management.admin import ScPombeStrainPage
from collection_management.admin import EColiStrainPage
from collection_management.admin import MammalianLinePage
from collection_management.admin import MammalianLineDocPage
from collection_management.admin import AntibodyPage

my_admin_site.register(SaCerevisiaeStrain, SaCerevisiaeStrainPage)
my_admin_site.register(Plasmid, PlasmidPage)
my_admin_site.register(Oligo, OligoPage)
my_admin_site.register(ScPombeStrain, ScPombeStrainPage)
my_admin_site.register(EColiStrain, EColiStrainPage)
my_admin_site.register(MammalianLineDoc, MammalianLineDocPage)
my_admin_site.register(MammalianLine, MammalianLinePage)
my_admin_site.register(Antibody, AntibodyPage)

#################################################
#             ORDER MANAGEMENT PAGES            #
#################################################

from order_management.models import CostUnit
from order_management.models import Location
from order_management.models import Order
from order_management.models import OrderExtraDoc
from order_management.models import MsdsForm

from order_management.admin import SearchFieldOptLocation, SearchFieldOptCostUnit, SearchFieldOptSupplier, SearchFieldOptPartDescription, OrderQLSchema
from order_management.admin import OrderExtraDocInline
from order_management.admin import AddOrderExtraDocInline
from order_management.admin import CostUnitPage
from order_management.admin import LocationPage
from order_management.admin import OrderPage
from order_management.admin import MsdsFormPage
from order_management.admin import OrderExtraDocPage

my_admin_site.register(Order, OrderPage)
my_admin_site.register(CostUnit, CostUnitPage)
my_admin_site.register(Location, LocationPage)
my_admin_site.register(MsdsForm, MsdsFormPage)
my_admin_site.register(OrderExtraDoc, OrderExtraDocPage)

#################################################
#            CUSTOM USER/GROUP PAGES            #
#################################################

my_admin_site.register(Group, GroupAdmin)
my_admin_site.register(User, UserAdmin)

from user_management.models import LabUser

from user_management.admin import LabUserAdmin

my_admin_site.unregister(User)
my_admin_site.register(User, LabUserAdmin)

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

from formz.models import NucleicAcidPurity
from formz.models import NucleicAcidRisk
from formz.models import GenTechMethod
from formz.models import FormZHeader
from formz.models import ZkbsPlasmid
from formz.models import ZkbsOncogene
from formz.models import ZkbsCellLine
from formz.models import FormZStorageLocation
from formz.models import Species

from formz.admin import NucleicAcidPurityPage
from formz.admin import NucleicAcidRiskPage
from formz.admin import GenTechMethodPage
from formz.admin import FormZProjectPage
from formz.admin import FormZBaseElementPage
from formz.admin import FormZHeaderPage
from formz.admin import ZkbsPlasmidPage
from formz.admin import ZkbsOncogenePage
from formz.admin import ZkbsCellLinePage
from formz.admin import FormZStorageLocationPage
from formz.admin import SpeciesPage

my_admin_site.register(NucleicAcidPurity, NucleicAcidPurityPage)
my_admin_site.register(NucleicAcidRisk, NucleicAcidRiskPage)
my_admin_site.register(GenTechMethod, GenTechMethodPage)
my_admin_site.register(FormZProject, FormZProjectPage)
my_admin_site.register(FormZBaseElement, FormZBaseElementPage)
my_admin_site.register(FormZHeader, FormZHeaderPage)
my_admin_site.register(ZkbsPlasmid, ZkbsPlasmidPage)
my_admin_site.register(ZkbsOncogene, ZkbsOncogenePage)
my_admin_site.register(ZkbsCellLine, ZkbsCellLinePage)
my_admin_site.register(FormZStorageLocation, FormZStorageLocationPage)
my_admin_site.register(Species, SpeciesPage)

#################################################
#               RECORD APPROVAL                 #
#################################################

from record_approval.models import RecordToBeApproved
from record_approval.admin import RecordToBeApprovedPage

my_admin_site.register(RecordToBeApproved, RecordToBeApprovedPage)