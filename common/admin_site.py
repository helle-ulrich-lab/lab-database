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
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import GroupAdmin
from django.contrib.auth.models import Group
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
from formz.admin import (
    FormZAdminSite,
    GenTechMethodAdmin,
    NucleicAcidPurityAdmin,
    NucleicAcidRiskAdmin,
    SequenceFeatureAdmin,
    SpeciesAdmin,
    ZkbsCellLineAdmin,
    ZkbsOncogeneAdmin,
    ZkbsPlasmidAdmin,
)
from formz.admin import (
    HeaderAdmin as FormZHeaderAdmin,
)
from formz.admin import (
    ProjectAdmin as FormZProjectAdmin,
)
from formz.admin import (
    StorageLocationAdmin as FormZStorageLocationAdmin,
)
from formz.models import (
    GenTechMethod,
    NucleicAcidPurity,
    NucleicAcidRisk,
    SequenceFeature,
    Species,
    ZkbsCellLine,
    ZkbsOncogene,
    ZkbsPlasmid,
)
from formz.models import (
    Header as FormZHeader,
)
from formz.models import (
    Project as FormZProject,
)
from formz.models import (
    StorageLocation as FormZStorageLocation,
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

from .admin import OwnUserAdmin

User = get_user_model()
SITE_TITLE = getattr(settings, "SITE_TITLE", "Lab DB")


class OwnAdminSite(OrderAdminSite, FormZAdminSite, admin.AdminSite):
    """Create a custom admin site called OwnAdminSite"""

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
admin_site = OwnAdminSite()
# Disable delete selected action
admin_site.disable_action("delete_selected")

admin_site.register(Group, GroupAdmin)
admin_site.register(User, OwnUserAdmin)

admin_site.register(NucleicAcidPurity, NucleicAcidPurityAdmin)
admin_site.register(NucleicAcidRisk, NucleicAcidRiskAdmin)
admin_site.register(GenTechMethod, GenTechMethodAdmin)
admin_site.register(FormZProject, FormZProjectAdmin)
admin_site.register(SequenceFeature, SequenceFeatureAdmin)
admin_site.register(FormZHeader, FormZHeaderAdmin)
admin_site.register(ZkbsPlasmid, ZkbsPlasmidAdmin)
admin_site.register(ZkbsOncogene, ZkbsOncogeneAdmin)
admin_site.register(ZkbsCellLine, ZkbsCellLineAdmin)
admin_site.register(FormZStorageLocation, FormZStorageLocationAdmin)
admin_site.register(Species, SpeciesAdmin)

admin_site.register(Task, TaskAdmin)
admin_site.register(CompletedTask, CompletedTaskAdmin)

admin_site.register(Order, OrderAdmin)
admin_site.register(CostUnit, CostUnitAdmin)
admin_site.register(Location, LocationAdmin)
admin_site.register(MsdsForm, MsdsFormAdmin)
admin_site.register(GhsSymbol, GhsSymbolAdmin)
admin_site.register(SignalWord, SignalWordAdmin)
admin_site.register(HazardStatement, HazardStatementAdmin)

admin_site.register(SaCerevisiaeStrain, SaCerevisiaeStrainAdmin)
admin_site.register(Plasmid, PlasmidAdmin)
admin_site.register(Oligo, OligoAdmin)
admin_site.register(ScPombeStrain, ScPombeStrainAdmin)
admin_site.register(EColiStrain, EColiStrainAdmin)
admin_site.register(CellLine, CellLineAdmin)
admin_site.register(Antibody, AntibodyAdmin)
admin_site.register(WormStrain, WormStrainAdmin)
admin_site.register(WormStrainAllele, WormStrainAlleleAdmin)
admin_site.register(Inhibitor, InhibitorAdmin)
admin_site.register(SiRna, SiRnaAdmin)

admin_site.register(Approval, ApprovalAdmin)
