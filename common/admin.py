from django.contrib import admin
from django.apps import apps
from django.contrib.auth.models import Group, User
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.urls import re_path
from django.http import HttpResponse
from django.http import Http404
from django.core.files.storage import default_storage

from django.conf import settings
SITE_TITLE = getattr(settings, 'SITE_TITLE', 'Lab DB')

import urllib.request, urllib.parse
import os
import re
import mimetypes

from formz.models import FormZBaseElement
from formz.models import FormZProject

from ordering.admin import OrderAdmin
from formz.admin import FormZAdmin

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
            re_path(r'uploads/(?P<url_path>.*)$', self.admin_view(self.uploads)),
            re_path(r'ove/(?P<url_path>.*)$', self.admin_view(self.ove_protected_view)),
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
            
            # Try creating pretty file name
            try:
                # Get app and model names
                url_path_split = url_path.split('/')
                app_name = url_path_split[0]
                model_name = url_path_split[1]

                # Get file name and extension
                file_name, file_ext = os.path.splitext(url_path_split[-1])

                # Get object
                if model_name.endswith('doc'):
                    obj_id = int(file_name.split('_')[-1])
                else:
                    obj_id = int(re.findall('\d+(?=_)', file_name + '_')[0])
                obj = apps.get_model(app_name, model_name).objects.get(id=obj_id)

                # Create file name
                download_file_name = f"{obj.download_file_name}{file_ext}"
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
#          COLLECTION MANAGEMENT PAGES          #
#################################################

from collection.models.sa_cerevisiae_strain import SaCerevisiaeStrain
from collection.models.plasmid import Plasmid
from collection.models.oligo import Oligo
from collection.models.sc_pombe_strain import ScPombeStrain
from collection.models.e_coli_strain import EColiStrain
from collection.models.cell_line import CellLine
from collection.models.cell_line import CellLineDoc
from collection.models.antibody import Antibody
from collection.models.worm_strain import WormStrain

from collection.admin.sa_cerevisiae_strain import SaCerevisiaeStrainPage
from collection.admin.plasmid import PlasmidPage
from collection.admin.oligo import OligoPage
from collection.admin.sc_pombe_strain import ScPombeStrainPage
from collection.admin.e_coli_strain import EColiStrainPage
from collection.admin.cell_line import CellLinePage
from collection.admin.cell_line import CellLineDocPage
from collection.admin.antibody import AntibodyPage
from collection.admin.worm_strain import WormStrainPage

main_admin_site.register(SaCerevisiaeStrain, SaCerevisiaeStrainPage)
main_admin_site.register(Plasmid, PlasmidPage)
main_admin_site.register(Oligo, OligoPage)
main_admin_site.register(ScPombeStrain, ScPombeStrainPage)
main_admin_site.register(EColiStrain, EColiStrainPage)
main_admin_site.register(CellLineDoc, CellLineDocPage)
main_admin_site.register(CellLine, CellLinePage)
main_admin_site.register(Antibody, AntibodyPage)
main_admin_site.register(WormStrain, WormStrainPage)

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

#################################################
#                  INHIBITOR                    #
#################################################

from collection.models.inhibitor import Inhibitor
from collection.admin.inhibitor import InhibitorPage

main_admin_site.register(Inhibitor, InhibitorPage)

#################################################
#                    siRNA                      #
#################################################

from collection.models.si_rna import SiRna
from collection.admin.si_rna import SiRnaPage

main_admin_site.register(SiRna, SiRnaPage)