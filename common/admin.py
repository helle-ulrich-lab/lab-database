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
from django.contrib import messages
from django.conf.urls import url
from django.http import HttpResponse
from django.http import Http404
from django.core.files.storage import default_storage

#################################################
#          DJANGO PROJECT SETTINGS              #
#################################################

from config.private_settings import SITE_TITLE

#################################################
#        ADDED FUNCTIONALITIES IMPORTS          #
#################################################

# Import/Export functionalities from django-import-export
from import_export import resources

# Http stuff
import http.cookiejar
import urllib.request, urllib.parse

# SnapGene
from snapgene.pyclasses.client import Client
from snapgene.pyclasses.config import Config

import datetime
import zmq
import os
import time
from bs4 import BeautifulSoup
import re
import mimetypes

#################################################
#                OTHER IMPORTS                  #
#################################################

from formz.models import FormZBaseElement
from formz.models import FormZProject
from .models import GeneralSetting

#################################################
#            CUSTOM ADMINS IMPORTS              #
#################################################

from ordering.admin import OrderAdmin
from formz.admin import FormZAdmin

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

class MyAdminSite(OrderAdmin, FormZAdmin, admin.AdminSite):
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
                
        urls = super(MyAdminSite, self).get_urls()
        # Note that custom urls get pushed to the list (not appended)
        # This doesn't work with urls += ...
        urls = super(MyAdminSite, self).get_formz_urls() + \
            super(MyAdminSite, self).get_order_urls() + [
            url(r'uploads/(?P<url_path>.*)$', self.admin_view(self.uploads)),
            url(r'^150freezer/$', self.freezer150_view),
            url(r'ove/(?P<url_path>.*)$', self.admin_view(self.ove_protected_view)),
            ] + \
            urls 
            
        return urls

    def uploads(self, request, *args, **kwargs):
        """Protected view for uploads/media files"""
        
        url_path = str(kwargs["url_path"])
        
        if default_storage.exists(url_path): # check if file exists
            
            # Create HttpResponse and add Content Type and, if present, Encoding
            response = HttpResponse()
            mimetype, encoding = mimetypes.guess_type(url_path)
            mimetype = mimetype if mimetype else 'application/octet-stream'
            response["Content-Type"] = mimetype
            if encoding:
                response["Content-Encoding"] = encoding

            download_file_name = os.path.basename(url_path)
            
            # Get app and model names
            try:
                url_path_split = url_path.split('/')
                app_name = url_path_split[0]
                model_name = url_path_split[1]
                file_name, file_ext = os.path.splitext(url_path_split[-1]) 

                # Generate name for download file
                if app_name == 'collection':

                    # Get object 
                    file_prefix = file_name.split('_')[0]

                    if model_name == 'celllinedoc':
                        obj_id = int(file_name.split('_')[-1])
                    else:
                        obj_id = int(re.findall('\d+(?=_)', file_name + '_')[0])
                    obj = apps.get_model(app_name, model_name).objects.get(id=obj_id)  

                    if model_name == 'celllinedoc':
                        obj_name = "{} - {} Doc# {}".format(obj.cell_line.name, obj.typ_e.title(), obj.id)
                    else:
                        obj_name = obj.name

                    download_file_name = "{} - {}{}".format(file_prefix, obj_name, file_ext).replace(',','')

                if model_name == 'msdsform':
                    obj_id = int(re.findall('\d+(?=_)', file_name + '_')[0])
                    obj = apps.get_model(app_name, model_name).objects.get(id=obj_id)  
                    download_file_name = obj.download_file_name
            
            except:
                pass

            # Needed for file names that include special, non ascii, characters 
            file_expr = "filename*=utf-8''{}".format(urllib.parse.quote(download_file_name))

            # Set content disposition based on file type
            if 'pdf' in mimetype.lower():
                response["Content-Disposition"] = 'inline; {}'.format(file_expr)
            elif 'png' in mimetype.lower():
                response["Content-Disposition"] = "{}".format(file_expr)
            else:
                response["Content-Disposition"] = 'attachment; {}'.format(file_expr)
            
            response['X-Accel-Redirect'] = "/secret/{url_path}".format(url_path=url_path)
            return response
            
        else:
            raise Http404

    def freezer150_view(self, request):
        """ View to show the temperature of the -150° C freezer """

        try:
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
            'date_time': date_time,
            'temperature': T
            }
        
        except:
            context = {
            'user': request.user,
            'site_header': self.site_header,
            'has_permission': self.has_permission(request), 
            'site_url': self.site_url, 
            'title':"-150° C Freezer", 
            'date_time': '',
            'temperature': ''
            }
        
        return render(request, 'admin/freezer150.html', context)

    def ove_protected_view(self, request, *args, **kwargs):
        """Put OVE behind Django's authentication system"""
        
        url_path = str(kwargs["url_path"])
        response = HttpResponse()
        
        # Content-Type must be explicitely passed
        # NGINX will not set it itself
        mimetype, encoding = mimetypes.guess_type(url_path)
        response["Content-Type"] = mimetype
        response['X-Accel-Redirect'] = "/ove_secret/{url_path}".format(url_path=url_path)
        return response

# Instantiate custom admin site 
main_admin_site = MyAdminSite()

# Disable delete selected action
main_admin_site.disable_action('delete_selected')

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

    def add_view(self, request, form_url='', extra_context=None):
        
        if GeneralSetting.objects.all().exists():
            # Override default add_view to prevent addition of new records, one is enough!
            messages.error(request, 'Nice try, you can only have one set of general settings')
            return HttpResponseRedirect("..")
        else:
            return super(GeneralSettingPage,self).add_view(request, form_url='', extra_context=None)

main_admin_site.register(GeneralSetting, GeneralSettingPage)

#################################################
#          COLLECTION MANAGEMENT PAGES          #
#################################################

from collection.models import SaCerevisiaeStrain
from collection.models import Plasmid
from collection.models import Oligo
from collection.models import ScPombeStrain
from collection.models import EColiStrain
from collection.models import CellLine
from collection.models import CellLineDoc
from collection.models import Antibody

from collection.admin import SaCerevisiaeStrainPage
from collection.admin import PlasmidPage
from collection.admin import OligoPage
from collection.admin import ScPombeStrainPage
from collection.admin import EColiStrainPage
from collection.admin import CellLinePage
from collection.admin import CellLineDocPage
from collection.admin import AntibodyPage

main_admin_site.register(SaCerevisiaeStrain, SaCerevisiaeStrainPage)
main_admin_site.register(Plasmid, PlasmidPage)
main_admin_site.register(Oligo, OligoPage)
main_admin_site.register(ScPombeStrain, ScPombeStrainPage)
main_admin_site.register(EColiStrain, EColiStrainPage)
main_admin_site.register(CellLineDoc, CellLineDocPage)
main_admin_site.register(CellLine, CellLinePage)
main_admin_site.register(Antibody, AntibodyPage)

#################################################
#             ORDER MANAGEMENT PAGES            #
#################################################

from ordering.models import CostUnit
from ordering.models import Location
from ordering.models import Order
from ordering.models import OrderExtraDoc
from ordering.models import MsdsForm
from ordering.models import GhsSymbol
from ordering.models import SignalWord
from ordering.models import HazardStatement

from ordering.admin import SearchFieldOptLocation, SearchFieldOptCostUnit, SearchFieldOptSupplier, SearchFieldOptPartDescription, OrderQLSchema
from ordering.admin import OrderExtraDocInline
from ordering.admin import AddOrderExtraDocInline
from ordering.admin import CostUnitPage
from ordering.admin import LocationPage
from ordering.admin import OrderPage
from ordering.admin import MsdsFormPage
from ordering.admin import OrderExtraDocPage
from ordering.admin import GhsSymbolPage
from ordering.admin import SignalWordPage
from ordering.admin import HazardStatementPage

main_admin_site.register(Order, OrderPage)
main_admin_site.register(CostUnit, CostUnitPage)
main_admin_site.register(Location, LocationPage)
main_admin_site.register(MsdsForm, MsdsFormPage)
main_admin_site.register(OrderExtraDoc, OrderExtraDocPage)
main_admin_site.register(GhsSymbol, GhsSymbolPage)
main_admin_site.register(SignalWord, SignalWordPage)
main_admin_site.register(HazardStatement, HazardStatementPage)

#################################################
#            CUSTOM USER/GROUP PAGES            #
#################################################

main_admin_site.register(Group, GroupAdmin)
main_admin_site.register(User, UserAdmin)

from extend_user.models import LabUser

from extend_user.admin import LabUserAdmin

main_admin_site.unregister(User)
main_admin_site.register(User, LabUserAdmin)

#################################################
#               BACKGROUND TASKS                #
#################################################

from background_task.models import Task
from background_task.models import CompletedTask

from background_task.admin import TaskAdmin
from background_task.admin import CompletedTaskAdmin

main_admin_site.register(Task, TaskAdmin)
main_admin_site.register(CompletedTask, CompletedTaskAdmin)

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

main_admin_site.register(NucleicAcidPurity, NucleicAcidPurityPage)
main_admin_site.register(NucleicAcidRisk, NucleicAcidRiskPage)
main_admin_site.register(GenTechMethod, GenTechMethodPage)
main_admin_site.register(FormZProject, FormZProjectPage)
main_admin_site.register(FormZBaseElement, FormZBaseElementPage)
main_admin_site.register(FormZHeader, FormZHeaderPage)
main_admin_site.register(ZkbsPlasmid, ZkbsPlasmidPage)
main_admin_site.register(ZkbsOncogene, ZkbsOncogenePage)
main_admin_site.register(ZkbsCellLine, ZkbsCellLinePage)
main_admin_site.register(FormZStorageLocation, FormZStorageLocationPage)
main_admin_site.register(Species, SpeciesPage)

#################################################
#               RECORD APPROVAL                 #
#################################################

from approval.models import RecordToBeApproved
from approval.admin import RecordToBeApprovedPage

main_admin_site.register(RecordToBeApproved, RecordToBeApprovedPage)