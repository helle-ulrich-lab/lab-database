import json
import os
import time
import urllib.parse
import zipfile
from collections import OrderedDict
from urllib.parse import quote as urlquote
from uuid import uuid4

import zmq
from background_task import background
from bs4 import BeautifulSoup
from django import forms
from django.apps import apps
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin.utils import unquote
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.core.mail import mail_admins
from django.db.models import CharField
from django.db.models.functions import Collate
from django.forms import TextInput
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import get_template
from django.urls import re_path, reverse
from django.utils import timezone
from django.utils.html import format_html
from djangoql.admin import DjangoQLSearchMixin
from djangoql.schema import DateTimeField, IntField, StrField
from guardian.admin import GuardedModelAdmin, UserManage
from guardian.shortcuts import (
    assign_perm,
    get_user_model,
    get_users_with_perms,
    remove_perm,
)

from collection.models import Oligo
from common.model_clone import CustomClonableModelAdmin
from common.shared import (
    AdminChangeFormWithNavigation,
    SimpleHistoryWithSummaryAdmin,
    ToggleDocInlineMixin,
)
from formz.models import (
    FormZBaseElement,
    FormZHeader,
    FormZProject,
    FormZStorageLocation,
    ZkbsCellLine,
)
from snapgene.pyclasses.client import Client
from snapgene.pyclasses.config import Config

BASE_DIR = settings.BASE_DIR
MEDIA_ROOT = settings.MEDIA_ROOT
LAB_ABBREVIATION_FOR_FILES = getattr(settings, "LAB_ABBREVIATION_FOR_FILES", "")
SNAPGENE_COMMON_FEATURES_PATH = os.path.join(
    BASE_DIR, "snapgene/standardCommonFeatures.ftrs"
)


################################
# DNA Map processing functions #
################################


def create_map_preview(
    obj, detect_common_features, attempt_number=3, messages=[], **kwargs
):
    """Given a path to a snapgene map, use snapegene server
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

            if detect_common_features:
                argument = {
                    "request": "detectFeatures",
                    "inputFile": obj.map.path,
                    "outputFile": obj.map.path,
                    "featureDatabase": SNAPGENE_COMMON_FEATURES_PATH,
                }
                r = client.requestResponse(argument, 10000)
                r_code = r.get("code", 1)
                if r_code > 0:
                    error_message = "detectFeatures - error " + r_code
                    if error_message not in messages:
                        messages.append(error_message)
                    client.close()
                    raise Exception

            argument = {
                "request": "generatePNGMap",
                "inputFile": obj.map.path,
                "outputPng": obj.map_png.path,
                "title": f"{kwargs['prefix'] if 'prefix' in kwargs else f'{obj._model_abbreviation}{LAB_ABBREVIATION_FOR_FILES}'}{obj.id} - {obj.name}",
                "showEnzymes": True,
                "showFeatures": True,
                "showPrimers": True,
                "showORFs": False,
            }
            r = client.requestResponse(argument, 10000)
            r_code = r.get("code", 1)
            if r_code > 0:
                error_message = "generatePNGMap - error " + r_code
                if error_message not in messages:
                    messages.append(error_message)
                client.close()
                raise Exception

            argument = {
                "request": "exportDNAFile",
                "inputFile": obj.map.path,
                "outputFile": obj.map_gbk.path,
                "exportFilter": "biosequence.gb",
            }
            r = client.requestResponse(argument, 10000)
            r_code = r.get("code", 1)
            if r_code > 0:
                error_message = "exportDNAFile - error " + r_code
                if error_message not in messages:
                    messages.append(error_message)
                client.close()
                raise Exception

            client.close()

        except:
            create_map_preview(
                obj, detect_common_features, attempt_number - 1, messages, **kwargs
            )

    else:
        mail_admins(
            "Snapgene server error",
            "There was an error with creating the preview for {} with snapgene server.\n\nErrors: {}.".format(
                obj.map.path, str(messages)
            ),
            fail_silently=True,
        )
        raise Exception


def get_map_features(obj, attempt_number=3, messages=[]):
    """Given a path to a snapgene map (.dna), use snapegene server
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

            argument = {"request": "reportFeatures", "inputFile": obj.map.path}
            r = client.requestResponse(argument, 10000)
            r_code = r.get("code", 1)
            if r_code > 0:
                error_message = "reportFeatures - error " + r_code
                if error_message not in messages:
                    messages.append(error_message)
                client.close()
                raise Exception

            client.close()

            plasmid_features = r.get("features", [])
            feature_names = [feat["name"].strip() for feat in plasmid_features]
            return feature_names

        except:
            get_map_features(obj.map.path, attempt_number - 1, messages)

    else:
        mail_admins(
            "Snapgene server error",
            "There was an error with getting plasmid features for {} with snapgene server.\n\nErrors: {}.".format(
                obj.map.path, str(messages)
            ),
            fail_silently=True,
        )
        raise Exception


def convert_map_gbk_to_dna(gbk_map_path, dna_map_path, attempt_number=3, messages=[]):
    """Given a path to a gbk  map (.gbk), use snapegene server
    to convert it to .dna"""

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

            argument = {
                "request": "importDNAFile",
                "inputFile": gbk_map_path,
                "outputFile": dna_map_path,
            }
            r = client.requestResponse(argument, 10000)
            r_code = r.get("code", 1)
            if r_code > 0:
                error_message = "importDNAFile - error " + r_code
                if error_message not in messages:
                    messages.append(error_message)
                client.close()
                raise Exception

            client.close()

        except:
            convert_map_gbk_to_dna(
                gbk_map_path, dna_map_path, attempt_number - 1, messages
            )

    else:
        mail_admins(
            "Snapgene server error",
            "There was an error converting a gbk map to dna for {} with snapgene server.\n\nErrors: {}.".format(
                gbk_map_path, str(messages)
            ),
            fail_silently=True,
        )
        raise Exception


#################################################
#                CUSTOM CLASSES                 #
#################################################


class Approval:
    def approval(self, instance):
        """Custom list_view field to show whether record has been approved or not"""

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

    # Added this try block because if user_auth table not present in DB
    # (e.g. very first migration) the following code runs and throws an exception
    try:
        user = forms.ChoiceField(
            choices=[("------", "------")]
            + [
                (u.username, u)
                for u in User.objects.all().order_by("last_name")
                if u.groups.filter(name="Regular lab member").exists()
            ],
            label="Username",
            error_messages={"does_not_exist": "This user is not valid"},
        )
        is_permanent = forms.BooleanField(required=False, label="Grant indefinitely?")
    except:
        pass


class SortAutocompleteResultsId(admin.ModelAdmin):

    def get_ordering(self, request):
        # Force sorting of autocompletion results to be by ascending id
        if request.path_info == "/autocomplete/":
            return ["id"]
        else:
            return super(SortAutocompleteResultsId, self).get_ordering(request)


@background(schedule=86400)  # Run 24 h after it is called, as "background" process
def delete_obj_perm_after_24h(perm, user_id, obj_id, app_label, model_name):
    """Delete object permession after 24 h"""

    user = User.objects.get(id=user_id)
    obj = apps.get_model(app_label, model_name).objects.get(id=obj_id)

    remove_perm(perm, user, obj)


def rename_info_sheet_save_obj_update_history(obj, new_obj):

    doc_dir_path = os.path.join(MEDIA_ROOT, obj._model_upload_to)
    old_file_name_abs_path = os.path.join(MEDIA_ROOT, obj.info_sheet.name)
    _, ext = os.path.splitext(os.path.basename(old_file_name_abs_path))
    now = timezone.now().strftime("%Y%m%d_%H%M%S_%f")
    new_file_name = os.path.join(
        obj._model_upload_to,
        f"{obj._model_abbreviation}{LAB_ABBREVIATION_FOR_FILES}{obj.id}_{now}{ext.lower()}",
    )
    new_file_name_abs_path = os.path.join(MEDIA_ROOT, new_file_name)

    # Create destination folder if it doesn't exist
    if not os.path.exists(doc_dir_path):
        os.makedirs(doc_dir_path)

    # Rename file
    os.rename(old_file_name_abs_path, new_file_name_abs_path)

    obj.info_sheet.name = new_file_name
    obj.save()

    # For new records, delete first history record, which contains the unformatted
    # info_sheet name, and change the newer history record's history_type from
    # changed (~) to created (+). This gets rid of a duplicate history record created
    # when automatically generating an info_sheet name
    if new_obj:
        obj.history.last().delete()
        history_obj = obj.history.first()
        history_obj.history_type = "+"
        history_obj.save()


class CollectionBaseAdmin(
    DjangoQLSearchMixin,
    SimpleHistoryWithSummaryAdmin,
    AdminChangeFormWithNavigation,
    ToggleDocInlineMixin,
    CustomClonableModelAdmin,
    admin.ModelAdmin,
):
    list_per_page = 25
    formfield_overrides = {
        CharField: {"widget": TextInput(attrs={"size": "93"})},
    }
    djangoql_completion_enabled_by_default = False
    obj_specific_fields = ()
    obj_unmodifiable_fields = ()
    add_view_fieldsets = None
    change_view_fieldsets = None
    history_array_fields = {}
    show_all_plasmids_in_stocked_strain = False
    is_guarded_model = False
    m2m_save_ignore_fields = []
    set_readonly_fields = []
    readonly_fields = []
    show_formz = False

    def save_history_fields(self, form, obj=None):

        obj = obj if obj else self.model.objects.get(pk=form.instance.id)

        history_array_fields = self.history_array_fields.copy()
        if self.m2m_save_ignore_fields:
            history_array_fields = {
                k: v
                for k, v in history_array_fields.items()
                if k not in self.m2m_save_ignore_fields
            }

        # Keep a record of the IDs of linked M2M fields in the main obj record
        # Not pretty, but it works

        for m2m_history_field_name, m2m_model in history_array_fields.items():

            try:
                m2m_set = getattr(obj, f"{m2m_history_field_name[8:]}")
            except:
                try:
                    m2m_set = getattr(obj, f"{m2m_model._meta.model_name}_set")
                except:
                    continue
            setattr(
                obj,
                m2m_history_field_name,
                (
                    list(
                        m2m_set.order_by("id")
                        .distinct("id")
                        .values_list("id", flat=True)
                    )
                    if m2m_set.exists()
                    else []
                ),
            )

        obj.save_without_historical_record()

        history_obj = obj.history.latest()
        for m2m_history_field_name, m2m_model in self.history_array_fields.items():
            setattr(
                history_obj,
                m2m_history_field_name,
                getattr(obj, m2m_history_field_name),
            )

        history_obj.save()

        return obj, history_obj

    def save_related(self, request, form, formsets, change):

        super().save_related(request, form, formsets, change)

        return self.save_history_fields(form)

    def add_view(self, request, form_url="", extra_context=None):

        self.fieldsets = self.add_view_fieldsets.copy()
        self.readonly_fields = self.set_readonly_fields + self.obj_unmodifiable_fields

        return super().add_view(request, form_url, extra_context)


class CollectionSimpleAdmin(CollectionBaseAdmin):

    def save_model(self, request, obj, form, change):

        rename_doc = False
        new_obj = False

        # New objects
        if obj.pk == None:

            # Don't rely on autoincrement value in DB table
            obj.id = (
                self.model.objects.order_by("-id").first().id + 1
                if self.model.objects.exists()
                else 1
            )

            try:
                obj.created_by
            except:
                obj.created_by = request.user

            if obj.info_sheet:
                rename_doc = True
                new_obj = True
            obj.save()

        # Existing objects
        else:
            saved_obj = self.model.objects.get(pk=obj.pk)

            # Check if info_sheet has been changed
            if obj.info_sheet and obj.info_sheet != saved_obj.info_sheet:
                rename_doc = True
                obj.save_without_historical_record()
            else:
                obj.save()

        # Rename info_sheet
        if rename_doc:
            rename_info_sheet_save_obj_update_history(obj, new_obj)

    def change_view(self, request, object_id, form_url="", extra_context=None):

        self.fieldsets = self.change_view_fieldsets.copy()
        self.readonly_fields = self.set_readonly_fields + self.obj_unmodifiable_fields

        return super().change_view(request, object_id, form_url, extra_context)

    @admin.action(description="Info Sheet")
    def get_sheet_short_name(self, instance):
        """Create custom column for information sheet.
        It formats <a> html element to show always View"""

        if instance.info_sheet:
            return format_html(
                '<a class="magnific-popup-iframe-pdflink" href="{}">View</a>',
                instance.info_sheet.url,
            )
        else:
            return ""


class CollectionUserProtectionAdmin(Approval, CollectionBaseAdmin):

    show_formz = True

    def save_model(self, request, obj, form, change):

        if obj.pk == None:

            # Don't rely on autoincrement value in DB table
            obj.id = (
                self.model.objects.order_by("-id").first().id + 1
                if self.model.objects.exists()
                else 1
            )
            obj.created_by = request.user
            obj.save()

            # Approve right away if the request's user is the PI.
            # If not, create an approval record
            if (
                request.user.labuser.is_principal_investigator
                and request.user.id
                in obj.formz_projects.all().values_list("project_leader__id", flat=True)
            ):
                original_last_changed_date_time = obj.last_changed_date_time
                obj.created_approval_by_pi = True
                obj.approval_user = request.user
                obj.approval_by_pi_date_time = timezone.now()
                obj.save_without_historical_record()
                self.model.objects.filter(id=obj.pk).update(
                    last_changed_date_time=original_last_changed_date_time
                )
            else:
                obj.approval.create(activity_type="created", activity_user=request.user)

        else:

            # If the disapprove button was clicked, no approval
            # record for the object exists, create one
            if "_disapprove_record" in request.POST:
                if not obj.approval.all().exists():
                    original_last_changed_date_time = obj.last_changed_date_time
                    obj.approval.create(
                        activity_type="changed", activity_user=obj.created_by
                    )
                    obj.last_changed_approval_by_pi = False
                    obj.save_without_historical_record()
                    self.model.objects.filter(id=obj.pk).update(
                        last_changed_date_time=original_last_changed_date_time
                    )
                return

            # Approve right away if the request's user is the principal investigator.
            #  If not, create an approval record
            if (
                request.user.labuser.is_principal_investigator
                and request.user.id
                in obj.formz_projects.all().values_list("project_leader__id", flat=True)
            ):
                obj.last_changed_approval_by_pi = True
                if not obj.created_approval_by_pi:
                    obj.created_approval_by_pi = True
                obj.approval_user = request.user
                obj.approval_by_pi_date_time = timezone.now()
                obj.save()

                if obj.approval.all().exists():
                    approval_records = obj.approval.all()
                    approval_records.delete()
            else:
                obj.last_changed_approval_by_pi = False
                obj.approval_user = None
                obj.save()

                # If an approval record for this object does not exist, create one
                if not obj.approval.all().exists():
                    obj.approval.create(
                        activity_type="changed", activity_user=request.user
                    )
                else:
                    # If an approval record for this object exists, check if a message was
                    # sent. If so, update the approval record's edited field
                    approval_obj = obj.approval.all().latest("message_date_time")
                    if approval_obj.message_date_time:
                        if obj.last_changed_date_time > approval_obj.message_date_time:
                            approval_obj.edited = True
                            approval_obj.save()

    def change_view(self, request, object_id, form_url="", extra_context=None):

        obj = self.model.objects.get(pk=object_id)
        self.can_change = False
        extra_context = extra_context or {}
        extra_context.update(
            {
                "show_close": True,
                "show_save_and_add_another": False,
                "show_save_and_continue": True,
                "show_save": True,
                "show_obj_permission": False,
                "show_disapprove": (
                    True
                    if request.user.groups.filter(name="Approval manager").exists()
                    else False
                ),
                "show_formz": self.show_formz,
            }
        )

        # Set fieldsets
        change_view_fieldsets = self.change_view_fieldsets.copy()
        # For approval view, uncollapse FormZ section
        if request.GET.get("_approval", "") and self.show_formz:
            formz_idx = next(
                filter(lambda f: f[1][0] == "FormZ", enumerate(change_view_fieldsets)),
                None,
            )
            if formz_idx:
                change_view_fieldsets[formz_idx[0]][1]["classes"] = tuple()
        self.fieldsets = change_view_fieldsets

        # If available, add plasmids in stocked strain to context
        if self.show_all_plasmids_in_stocked_strain:
            extra_context["plasmid_id_list"] = tuple(
                obj.history_all_plasmids_in_stocked_strain
            )

        if (
            request.user == obj.created_by
            or request.user.groups.filter(name="Lab manager").exists()
            or request.user.labuser.is_principal_investigator
            or request.user.is_superuser
        ):

            self.can_change = True

            if self.is_guarded_model:
                extra_context.update({"show_obj_permission": True})

        elif self.is_guarded_model and request.user.has_perm(
            f"{self.model._meta.app_label}.change_{self.model._meta.model_name}", obj
        ):
            self.can_change = True

        # Read-only fields
        readonly_fields = (
            self.set_readonly_fields
            + self.obj_specific_fields
            + self.obj_unmodifiable_fields
        )
        if self.can_change:
            readonly_fields = self.set_readonly_fields + self.obj_unmodifiable_fields
        self.readonly_fields = readonly_fields

        return super().change_view(request, object_id, form_url, extra_context)

    def response_change(self, request, obj):

        # If the disapprove button is clicked, redirect to the approval
        # record changepage
        if "_disapprove_record" in request.POST:
            msg_dict = {
                "name": self.model._meta.verbose_name,
                "obj": format_html('<a href="{}">{}</a>', urlquote(request.path), obj),
            }
            msg = format_html('The {name} "{obj}" was disapproved.', **msg_dict)
            self.message_user(request, msg, messages.SUCCESS)
            return HttpResponseRedirect(
                reverse(
                    "admin:approval_recordtobeapproved_change",
                    args=(obj.approval.latest("created_date_time").id,),
                )
            )

        return super().response_change(request, obj)


class CustomGuardedModelAdmin(GuardedModelAdmin):

    is_guarded_model = True

    def get_urls(self):
        """
        Extends standard guardian admin model urls with delete url
        """

        urls = super(CustomGuardedModelAdmin, self).get_urls()

        info = self.model._meta.app_label, self.model._meta.model_name
        myurls = [
            re_path(
                r"^(?P<object_pk>.+)/permissions/(?P<user_id>\-?\d+)/remove/$",
                view=self.admin_site.admin_view(self.obj_perms_delete),
                name="%s_%s_permissions_delete" % info,
            )
        ]
        urls = myurls + urls

        return urls

    def obj_perms_manage_view(self, request, object_pk):
        """
        Override main guardian object permissions view.
        Only for users, not groups
        Assign object-specific change permission to specific users
        Allow permissions to be granted for 24 h
        """

        if not self.has_change_permission(request, None):
            post_url = reverse("admin:index", current_app=self.admin_site.name)
            return redirect(post_url)

        obj = get_object_or_404(self.get_queryset(request), pk=unquote(object_pk))
        users_perms = OrderedDict(
            sorted(
                get_users_with_perms(
                    obj, attach_perms=True, with_group_users=False
                ).items(),
                key=lambda user: getattr(user[0], get_user_model().USERNAME_FIELD),
            )
        )

        if not (
            request.user.is_superuser
            or request.user.groups.filter(name="Lab manager").exists()
            or request.user == obj.created_by
            or request.user.labuser.is_principal_investigator
        ):
            raise PermissionDenied()

        if request.method == "POST" and "submit_manage_user" in request.POST:

            user_form = self.get_obj_perms_user_select_form(request)(request.POST)
            if user_form.is_valid():

                perm = "{}.change_{}".format(
                    self.model._meta.app_label, self.model._meta.model_name
                )
                user = User.objects.get(username=request.POST["user"])
                assign_perm(perm, user, obj)
                self.message_user(request, "Permissions saved.", messages.SUCCESS)

                # If "Grant indefinitely" not selected remove permission after 24 h
                if not request.POST.get("is_permanent", False):
                    delete_obj_perm_after_24h(
                        perm, user.id, obj.id, obj._meta.app_label, obj._meta.model_name
                    )

                return HttpResponseRedirect(".")
        else:
            user_form = self.get_obj_perms_user_select_form(request)()

        context = self.get_obj_perms_base_context(request, obj)
        context["users_perms"] = users_perms
        context["user_form"] = user_form

        # https://github.com/django/django/commit/cf1f36bb6eb34fafe6c224003ad585a647f6117b
        request.current_app = self.admin_site.name

        return render(request, self.get_obj_perms_manage_template(), context)

    def obj_perms_manage_user_view(self, request, object_pk, user_id):
        """
        Forbid using this view
        """

        raise PermissionDenied

    def get_obj_perms_user_select_form(self, request):
        """
        Returns form class for selecting a user for permissions management.
        By default :form:`UserManage` is returned.
        """

        return CustomUserManage

    def obj_perms_delete(self, request, object_pk, user_id):
        """Delete object permission for a user"""

        user = get_object_or_404(get_user_model(), pk=user_id)
        obj = get_object_or_404(self.get_queryset(request), pk=object_pk)

        remove_perm(
            "{}.change_{}".format(
                self.model._meta.app_label, self.model._meta.model_name
            ),
            user,
            obj,
        )
        self.message_user(request, "Permission removed.", messages.SUCCESS)

        return HttpResponseRedirect("../..")


class AdminOligosInMap(admin.ModelAdmin):

    def get_urls(self):
        """
        Add navigation url
        """

        urls = super(AdminOligosInMap, self).get_urls()

        urls = [
            re_path(r"^(?P<object_id>.+)/find_oligos/$", view=self.find_oligos_in_map)
        ] + urls

        return urls

    def find_oligos_in_map(
        self, request, attempt_number=3, messages=[], *args, **kwargs
    ):
        """Given a path to a snapgene plasmid map, use snapegene server
        to detect common features and create map preview as png
        and gbk"""

        file_format = request.GET.get("file_format", "gbk")

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
                gbk_temp_path = os.path.join(temp_dir_path, f"{str(uuid4())}.gb")

                # Write oligos to file
                if not Oligo.objects.exists():
                    return HttpResponseNotFound
                oligos = (
                    Oligo.objects.annotate(
                        sequence_deterministic=Collate("sequence", "und-x-icu")
                    )
                    .filter(sequence_deterministic__iregex=r"^[ATCG]+$", length__gte=15)
                    .values_list("id", "sequence")
                )
                oligos = list(
                    {
                        "Name": f"! o{LAB_ABBREVIATION_FOR_FILES}{i[0]}",
                        "Sequence": i[1],
                        "Notes": "",
                    }
                    for i in oligos
                )
                with open(oligos_json_path, "w") as fhandle:
                    json.dump(oligos, fhandle)

                # Find oligos in object map and convert result to gbk
                obj = self.model.objects.get(id=kwargs["object_id"])
                argument = {
                    "request": "importPrimersFromList",
                    "inputFile": obj.map.path,
                    "inputPrimersFile": oligos_json_path,
                    "outputFile": dna_temp_path,
                }
                r = client.requestResponse(argument, 60000)
                r_code = r.get("code", 1)
                if r_code > 0:
                    error_message = "importPrimersFromList - error " + r_code
                    if error_message not in messages:
                        messages.append(error_message)
                    client.close()
                    raise Exception

                # If user wants to download file, then do so
                if file_format == "dna":
                    client.close()
                    # Get processed .dna map and delete temp files
                    with open(dna_temp_path, "rb") as fhandle:
                        file_data = fhandle.read()

                    # os.unlink(oligos_json_path)
                    os.unlink(dna_temp_path)

                    # Send response
                    response = HttpResponse(
                        file_data, content_type="application/octet-stream"
                    )
                    file_name = (
                        f"{obj._model_abbreviation}{LAB_ABBREVIATION_FOR_FILES}{obj.id}"
                        + f" - {obj.name} (imported oligos).dna"
                    )
                    response["Content-Disposition"] = (
                        f"attachment; filename*=utf-8''{urllib.parse.quote(file_name)}"
                    )
                    return response

                argument = {
                    "request": "exportDNAFile",
                    "inputFile": dna_temp_path,
                    "outputFile": gbk_temp_path,
                    "exportFilter": "biosequence.gb",
                }
                r = client.requestResponse(argument, 10000)
                r_code = r.get("code", 1)
                if r_code > 0:
                    error_message = "exportDNAFile - error " + r_code
                    if error_message not in messages:
                        messages.append(error_message)
                    client.close()
                    raise Exception

                client.close()

                # Get processed .gbk map and delete temp files
                with open(gbk_temp_path, "r") as fhandle:
                    file_data = fhandle.read()

                os.unlink(oligos_json_path)
                os.unlink(dna_temp_path)
                os.unlink(gbk_temp_path)

                # Send response
                response = HttpResponse(file_data, content_type="text/plain")
                response["Content-Disposition"] = (
                    'attachment; filename="map_with_imported_oligos.gbk"'
                )
                return response

            except Exception as err:
                messages.append(str(err))
                self.find_oligos_in_map(
                    request, attempt_number - 1, messages, *args, **kwargs
                )
        else:
            mail_admins(
                f"Error finding oligos in {obj._meta.verbose_name}",
                "There was an error with finding oligos in "
                f"{obj._meta.verbose_name} {kwargs['object_id']} "
                f"with snapgene server.\n\nErrors: {messages}.",
                fail_silently=True,
            )
            raise Exception


class FormUniqueNameCheck:

    def clean_name(self):
        """Check if name is unique before saving"""

        if not self.instance.pk:
            if self.instance._meta.model.objects.filter(
                name=self.cleaned_data["name"]
            ).exists():
                raise forms.ValidationError("Plasmid with this name already exists.")
            else:
                return self.cleaned_data["name"]
        else:
            if (
                self.instance._meta.model.objects.filter(name=self.cleaned_data["name"])
                .exclude(id=self.instance.pk)
                .exists()
            ):
                raise forms.ValidationError("Plasmid with this name already exists.")
            else:
                return self.cleaned_data["name"]


class FormTwoMapChangeCheck:

    def clean(self):
        """Check if both the .dna and .gbk map is changed at the same time, which
        is not allowed"""

        map_dna = self.cleaned_data.get("map", None)
        map_gbk = self.cleaned_data.get("map_gbk", None)

        if not self.instance.pk:
            if map_dna and map_gbk:
                self.add_error(
                    None,
                    "You cannot add both a .dna and a .gbk map at the same time. Please choose only one",
                )

        else:
            saved_obj = self.instance._meta.model.objects.get(id=self.instance.pk)
            saved_dna_map = saved_obj.map.name if saved_obj.map.name else None
            saved_gbk_map = saved_obj.map_gbk.name if saved_obj.map_gbk.name else None

            if map_dna != saved_dna_map and map_gbk != saved_gbk_map:
                self.add_error(
                    None,
                    "You cannot change both a .dna and a .gbk map at the same time. Please choose only one",
                )

        return self.cleaned_data


#################################################
#             CUSTOM SEARCH OPTIONS             #
#################################################


class FieldUse(StrField):

    name = "use"

    def get_lookup_name(self):
        return "us_e"


class FieldLocation(StrField):

    name = "location"

    def get_lookup_name(self):
        return "l_ocation"


class FieldApplication(StrField):

    name = "application"

    def get_lookup_name(self):
        return "a_pplication"


class FieldCreated(DateTimeField):

    name = "created_timestamp"

    def get_lookup_name(self):
        return "created_date_time"


class FieldLastChanged(DateTimeField):

    name = "last_changed_timestamp"

    def get_lookup_name(self):
        return "last_changed_date_time"


class FieldIntegratedPlasmidM2M(IntField):

    name = "integrated_plasmids_id"

    def get_lookup_name(self):
        return "integrated_plasmids__id"


class FieldCassettePlasmidM2M(IntField):

    name = "cassette_plasmids_id"

    def get_lookup_name(self):
        return "cassette_plasmids__id"


class FieldEpisomalPlasmidM2M(IntField):

    name = "episomal_plasmids_id"

    def get_lookup_name(self):
        return "episomal_plasmids__id"


class FieldFormZProject(StrField):

    name = "formz_projects_title"
    suggest_options = True

    def get_options(self, search):
        return FormZProject.objects.all().values_list("short_title", flat=True)

    def get_lookup_name(self):
        return "formz_projects__short_title"


class FieldParent1(IntField):

    name = "parent_1_id"

    def get_lookup_name(self):
        return "parent_1__id"


class FieldParent2(IntField):

    name = "parent_2_id"

    def get_lookup_name(self):
        return "parent_2__id"


class FieldFormZBaseElement(StrField):

    name = "formz_elements_name"
    suggest_options = True

    def get_options(self, search):

        if len(search) < 3:
            return ["Type 3 or more characters to see suggestions"]
        else:
            return FormZBaseElement.objects.filter(name__icontains=search).values_list(
                "name", flat=True
            )

    def get_lookup_name(self):
        return "formz_elements__name"


#################################################
#          DOWNLOAD FORMBLATT Z ACTION          #
#################################################


@admin.action(description="Export Formblatt Z for selected items")
def formz_as_html(modeladmin, request, queryset):
    """Export ForblattZ as html"""

    def get_params(app_label, model_name, obj_id):

        model = apps.get_model(app_label, model_name)
        model_content_type = ContentType.objects.get(
            app_label=app_label, model=model_name
        )
        opts = model._meta
        obj = model.objects.get(id=int(obj_id))

        # Get storage location object or create a new 'empty' one
        if FormZStorageLocation.objects.get(collection_model=model_content_type):
            storage_location = FormZStorageLocation.objects.get(
                collection_model=model_content_type
            )
        else:
            storage_location = FormZStorageLocation(
                collection_model=None,
                storage_location=None,
                species_name=None,
                species_risk_group=None,
            )

        if FormZHeader.objects.all().first():
            formz_header = FormZHeader.objects.all().first()
        else:
            formz_header = None

        obj.common_formz_elements = obj.get_all_common_formz_elements()
        obj.uncommon_formz_elements = obj.get_all_uncommon_formz_elements()
        obj.instock_plasmids = obj.get_all_instock_plasmids()
        obj.transient_episomal_plasmids = obj.get_all_transient_episomal_plasmids()

        if model_name == "cellline":
            storage_location.species_name = obj.organism
            storage_location.species_name_str = obj.organism.name_for_search
            storage_location.species_risk_group = obj.organism.risk_group
            obj.s2_plasmids = (
                obj.celllineepisomalplasmid_set.all()
                .filter(s2_work_episomal_plasmid=True)
                .distinct()
                .order_by("id")
            )
            transfected = True
            try:
                virus_packaging_cell_line = ZkbsCellLine.objects.filter(
                    name__iexact="293T (HEK 293T)"
                ).order_by("id")[0]
            except:
                virus_packaging_cell_line = ZkbsCellLine(name="293T (HEK 293T)")
        elif model_name == "wormstrain":
            transfected = False
            virus_packaging_cell_line = None
            storage_location.species_name_str = obj.get_organism_display()
        else:
            storage_location.species_name_str = (
                storage_location.species_name.name_for_search
            )
            obj.s2_plasmids = None
            transfected = False
            virus_packaging_cell_line = None

        params = {
            "object": obj,
            "storage_location": storage_location,
            "formz_header": formz_header,
            "transfected": transfected,
            "virus_packaging_cell_line": virus_packaging_cell_line,
        }

        return params

    response = HttpResponse(content_type="application/zip")
    response["Content-Disposition"] = (
        'attachment; filename="formblattz_{}_{}.zip'.format(
            time.strftime("%Y%m%d"), time.strftime("%H%M%S")
        )
    )

    template = get_template("admin/formz/formz_for_export.html")
    app_label = queryset[0]._meta.app_label
    model_name = queryset[0].__class__.__name__

    # Generates zip file

    with zipfile.ZipFile(response, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for obj in queryset:
            params = get_params(app_label, model_name.lower(), obj.id)
            params["map_attachment_type"] = request.POST.get(
                "map_attachment_type", default="none"
            )
            html = template.render(params)
            html = BeautifulSoup(html, features="lxml")
            html = html.prettify("utf-8")
            zip_file.writestr("{}_{}.html".format(model_name, obj.id), html)

    return response
