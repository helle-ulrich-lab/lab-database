import mimetypes
import os
import re
import urllib.parse
import urllib.request

from background_task.admin import CompletedTaskAdmin, TaskAdmin
from background_task.models import CompletedTask, Task
from django.apps import apps
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User
from django.core.files.storage import default_storage
from django.http import Http404, HttpResponse
from django.urls import re_path

from approval.admin import ApprovalAdmin
from approval.models import Approval
from collection.admin import (
    AntibodyAdmin,
    CellLineAdmin,
    EColiStrainAdmin,
    InhibitorAdmin,
    OligoAdmin,
    PlasmidAdmin,
    SaCerevisiaeStrainAdmin,
    ScPombeStrainAdmin,
    SiRnaAdmin,
    WormStrainAdmin,
    WormStrainAlleleAdmin,
)
from collection.models import (
    Antibody,
    CellLine,
    EColiStrain,
    Inhibitor,
    Oligo,
    Plasmid,
    SaCerevisiaeStrain,
    ScPombeStrain,
    SiRna,
    WormStrain,
    WormStrainAllele,
)
from extend_user.admin import LabUserAdmin
from formz.admin import (
    FormZAdmin,
    FormZBaseElementPage,
    FormZHeaderPage,
    FormZProjectPage,
    FormZStorageLocationPage,
    GenTechMethodPage,
    NucleicAcidPurityPage,
    NucleicAcidRiskPage,
    SpeciesPage,
    ZkbsCellLinePage,
    ZkbsOncogenePage,
    ZkbsPlasmidPage,
)
from formz.models import (
    FormZBaseElement,
    FormZHeader,
    FormZProject,
    FormZStorageLocation,
    GenTechMethod,
    NucleicAcidPurity,
    NucleicAcidRisk,
    Species,
    ZkbsCellLine,
    ZkbsOncogene,
    ZkbsPlasmid,
)
from ordering.admin import (
    CostUnitAdmin,
    GhsSymbolAdmin,
    HazardStatementAdmin,
    LocationAdmin,
    MsdsFormAdmin,
    OrderAdmin,
    OrderAdminSite,
    SignalWordAdmin,
)
from ordering.models import (
    CostUnit,
    GhsSymbol,
    HazardStatement,
    Location,
    MsdsForm,
    Order,
    SignalWord,
)

SITE_TITLE = getattr(settings, "SITE_TITLE", "Lab DB")


class MyAdminSite(OrderAdminSite, FormZAdmin, admin.AdminSite):
    """Create a custom admin site called MyAdminSite"""

    # Text to put at the end of each page's <title>.
    site_title = SITE_TITLE

    # Text to put in each page's <h1>.
    site_header = SITE_TITLE

    # Text to put at the top of the admin index page.
    index_title = "Home"

    # URL for the "View site" link at the top of each admin page.
    site_url = "/"

    def get_urls(self):
        urls = super().get_urls()
        # Note that custom urls get pushed to the list (not appended)
        # This doesn't work with urls += ...
        urls = (
            super().get_formz_urls()
            + super().get_order_urls()
            + [
                re_path(r"uploads/(?P<url_path>.*)$", self.admin_view(self.uploads)),
                re_path(
                    r"ove/(?P<url_path>.*)$", self.admin_view(self.ove_protected_view)
                ),
            ]
            + urls
        )

        return urls

    def uploads(self, request, *args, **kwargs):
        """Protected view for uploads/media files"""

        url_path = str(kwargs["url_path"])

        if default_storage.exists(url_path):  # check if file exists
            # Create HttpResponse and add Content Type and, if present, Encoding
            response = HttpResponse()
            mimetype, encoding = mimetypes.guess_type(url_path)
            mimetype = mimetype if mimetype else "application/octet-stream"
            response["Content-Type"] = mimetype
            if encoding:
                response["Content-Encoding"] = encoding

            download_file_name = os.path.basename(url_path)

            # Try creating pretty file name
            try:
                # Get app and model names
                url_path_split = url_path.split("/")
                app_name = url_path_split[0]
                model_name = url_path_split[1]

                # Get file name and extension
                file_name, file_ext = os.path.splitext(url_path_split[-1])

                # Get object
                if model_name.endswith("doc"):
                    obj_id = int(file_name.split("_")[-1])
                else:
                    obj_id = int(re.findall(r"\d+(?=_)", file_name + "_")[0])
                obj = apps.get_model(app_name, model_name).objects.get(id=obj_id)

                # Create file name
                download_file_name = f"{obj.download_file_name}{file_ext}"
            except Exception:
                pass

            # Needed for file names that include special, non ascii, characters
            file_expr = "filename*=utf-8''{}".format(
                urllib.parse.quote(download_file_name)
            )

            # Set content disposition based on file type
            if "pdf" in mimetype.lower():
                response["Content-Disposition"] = "inline; {}".format(file_expr)
            elif "png" in mimetype.lower():
                response["Content-Disposition"] = "{}".format(file_expr)
            else:
                response["Content-Disposition"] = "attachment; {}".format(file_expr)

            response["X-Accel-Redirect"] = "/secret/{url_path}".format(
                url_path=url_path
            )
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
        response["X-Accel-Redirect"] = "/ove_secret/{url_path}".format(
            url_path=url_path
        )
        return response


# Instantiate custom admin site
main_admin_site = MyAdminSite()
# Disable delete selected action
main_admin_site.disable_action("delete_selected")

main_admin_site.register(Group, GroupAdmin)
main_admin_site.register(User, UserAdmin)
main_admin_site.unregister(User)
main_admin_site.register(User, LabUserAdmin)

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

main_admin_site.register(Task, TaskAdmin)
main_admin_site.register(CompletedTask, CompletedTaskAdmin)

main_admin_site.register(Order, OrderAdmin)
main_admin_site.register(CostUnit, CostUnitAdmin)
main_admin_site.register(Location, LocationAdmin)
main_admin_site.register(MsdsForm, MsdsFormAdmin)
main_admin_site.register(GhsSymbol, GhsSymbolAdmin)
main_admin_site.register(SignalWord, SignalWordAdmin)
main_admin_site.register(HazardStatement, HazardStatementAdmin)

main_admin_site.register(SaCerevisiaeStrain, SaCerevisiaeStrainAdmin)
main_admin_site.register(Plasmid, PlasmidAdmin)
main_admin_site.register(Oligo, OligoAdmin)
main_admin_site.register(ScPombeStrain, ScPombeStrainAdmin)
main_admin_site.register(EColiStrain, EColiStrainAdmin)
main_admin_site.register(CellLine, CellLineAdmin)
main_admin_site.register(Antibody, AntibodyAdmin)
main_admin_site.register(WormStrain, WormStrainAdmin)
main_admin_site.register(WormStrainAllele, WormStrainAlleleAdmin)
main_admin_site.register(Inhibitor, InhibitorAdmin)
main_admin_site.register(SiRna, SiRnaAdmin)

main_admin_site.register(Approval, ApprovalAdmin)
