import os

from django.conf import settings
from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from common.admin import (
    AddDocFileInlineMixin,
    DocFileInlineMixin,
)
from formz.actions import formz_as_html
from formz.models import SequenceFeature

from ..shared.admin import (
    AdminOligosInMap,
    CollectionUserProtectionAdmin,
    CustomGuardedModelAdmin,
    SortAutocompleteResultsId,
    convert_map_gbk_to_dna,
    create_map_preview,
    get_map_features,
)
from .actions import export_plasmid
from .forms import PlasmidAdminForm
from .models import PlasmidDoc
from .search import PlasmidQLSchema

MEDIA_ROOT = settings.MEDIA_ROOT
LAB_ABBREVIATION_FOR_FILES = getattr(settings, "LAB_ABBREVIATION_FOR_FILES", "")
DEFAULT_ECOLI_STRAIN_IDS = getattr(settings, "DEFAULT_ECOLI_STRAIN_IDS", [])


class PlasmidDocInline(DocFileInlineMixin):
    """Inline to view existing plasmid documents"""

    model = PlasmidDoc


class PlasmidAddDocInline(AddDocFileInlineMixin):
    """Inline to add new plasmid documents"""

    model = PlasmidDoc


class PlasmidAdmin(
    SortAutocompleteResultsId,
    CustomGuardedModelAdmin,
    CollectionUserProtectionAdmin,
    AdminOligosInMap,
):
    list_display = (
        "id",
        "name",
        "selection",
        "get_map_short_name",
        "created_by",
        "approval",
    )
    list_display_links = ("id",)
    djangoql_schema = PlasmidQLSchema
    actions = [export_plasmid, formz_as_html]
    search_fields = ["id", "name"]
    autocomplete_fields = [
        "parent_vector",
        "formz_projects",
        "sequence_features",
        "vector_zkbs",
        "formz_ecoli_strains",
        "formz_gentech_methods",
    ]
    inlines = [PlasmidDocInline, PlasmidAddDocInline]
    form = PlasmidAdminForm
    change_form_template = "admin/collection/plasmid/change_form.html"
    add_form_template = "admin/collection/plasmid/change_form.html"
    clone_ignore_fields = ["map", "map_gbk", "map_png", "destroyed_date"]
    obj_unmodifiable_fields = [
        "created_date_time",
        "created_approval_by_pi",
        "last_changed_date_time",
        "last_changed_approval_by_pi",
        "created_by",
    ]
    obj_specific_fields = [
        "name",
        "other_name",
        "parent_vector",
        "selection",
        "us_e",
        "construction_feature",
        "received_from",
        "note",
        "reference",
        "map",
        "map_png",
        "map_gbk",
        "formz_projects",
        "formz_risk_group",
        "vector_zkbs",
        "formz_gentech_methods",
        "sequence_features",
        "formz_ecoli_strains",
        "destroyed_date",
    ]
    set_readonly_fields = [
        "map_png",
    ]
    add_view_fieldsets = [
        [
            None,
            {"fields": obj_specific_fields[:10] + obj_specific_fields[11:12]},
        ],
        [
            "FormZ",
            {
                "classes": tuple(),
                "fields": obj_specific_fields[12:],
            },
        ],
    ]
    change_view_fieldsets = [
        [
            None,
            {"fields": obj_specific_fields[:12] + obj_unmodifiable_fields},
        ],
        [
            "FormZ",
            {
                "classes": (("collapse",)),
                "fields": obj_specific_fields[12:],
            },
        ],
    ]

    def save_model(self, request, obj, form, change):
        rename_and_preview = False
        self.rename_and_preview = False
        new_obj = False
        self.new_obj = False
        self.clear_sequence_features = False
        convert_map_to_dna = False

        if obj.pk is None:
            obj.id = (
                self.model.objects.order_by("-id").first().id + 1
                if self.model.objects.exists()
                else 1
            )
            obj.created_by = request.user
            obj.save()
            new_obj = True
            self.new_obj = True

            # If a plasmid is 'Saved as new', clear all form Z elements
            if "_saveasnew" in request.POST and (obj.map or obj.map_gbk):
                self.clear_sequence_features = True

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
            if (
                request.user.is_pi
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
            # Check if the disapprove button was clicked. If so, and no approval
            # record for the object exists, create one
            if "_disapprove_record" in request.POST:
                if not obj.approval.all():
                    original_last_changed_date_time = obj.last_changed_date_time
                    obj.approval.create(
                        activity_type="changed", activity_user=obj.created_by
                    )
                    obj.last_changed_approval_by_pi = False
                    obj.approval_user = None
                    obj.save_without_historical_record()
                    self.model.objects.filter(id=obj.pk).update(
                        last_changed_date_time=original_last_changed_date_time
                    )
                return

            # Approve right away if the request's user is the principal investigator. If not,
            # create an approval record
            if (
                request.user.is_pi
                and request.user.id
                in obj.formz_projects.all().values_list("project_leader__id", flat=True)
            ):
                obj.last_changed_approval_by_pi = True
                if not obj.created_approval_by_pi:
                    obj.created_approval_by_pi = True  # Set created_approval_by_pi to True, should it still be None or False
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
                    obj.approval.create(
                        activity_type="changed", activity_user=request.user
                    )
                else:
                    # If an approval record for this object exists, check if a message was
                    # sent. If so, update the approval record's edited field
                    approval_obj = obj.approval.all().latest("message_date_time")
                    if approval_obj.message_date_time:
                        if timezone.now() > approval_obj.message_date_time:
                            approval_obj.edited = True
                            approval_obj.save()

            saved_obj = self.model.objects.get(pk=obj.pk)

            if obj.map != saved_obj.map or obj.map_gbk != saved_obj.map_gbk:
                if (obj.map and obj.map_gbk) or (
                    not saved_obj.map and not saved_obj.map_gbk
                ):
                    rename_and_preview = True
                    self.rename_and_preview = True
                    obj.save_without_historical_record()

                    if obj.map_gbk != saved_obj.map_gbk:
                        convert_map_to_dna = True

                else:
                    obj.map.name = ""
                    obj.map_png.name = ""
                    obj.map_gbk.name = ""
                    self.clear_sequence_features = True
                    obj.save()

            else:
                obj.save()

        # Rename map
        if rename_and_preview:
            now = timezone.now().strftime("%Y%m%d_%H%M%S_%f")
            new_file_name = (
                f"{obj._model_abbreviation}{LAB_ABBREVIATION_FOR_FILES}{obj.id}_{now}"
            )

            new_dna_file_name = os.path.join(
                obj._model_upload_to + "dna/", new_file_name + ".dna"
            )
            new_gbk_file_name = os.path.join(
                obj._model_upload_to + "gbk/", new_file_name + ".gbk"
            )
            new_png_file_name = os.path.join(
                obj._model_upload_to + "png/", new_file_name + ".png"
            )

            new_dna_file_path = os.path.join(MEDIA_ROOT, new_dna_file_name)
            new_gbk_file_path = os.path.join(MEDIA_ROOT, new_gbk_file_name)

            if convert_map_to_dna:
                old_gbk_file_path = obj.map_gbk.path
                os.rename(old_gbk_file_path, new_gbk_file_path)
                try:
                    convert_map_gbk_to_dna(new_gbk_file_path, new_dna_file_path)
                except Exception:
                    messages.error(
                        request,
                        "There was an error with converting the map to .gbk.",
                    )
            else:
                old_dna_file_path = obj.map.path
                os.rename(old_dna_file_path, new_dna_file_path)

            obj.map.name = new_dna_file_name
            obj.map_png.name = new_png_file_name
            obj.map_gbk.name = new_gbk_file_name
            obj.save()

            # For new records, delete first history record, which contains the unformatted
            # map name, and change the newer history record's history_type from changed (~)
            # to created (+). This gets rid of a duplicate history record created when
            # automatically generating a map name
            if new_obj:
                obj.history.last().delete()
                history_obj = obj.history.first()
                history_obj.history_type = "+"
                history_obj.save()

            # For map, detect common features and save as png
            try:
                detect_common_features_map_dna = request.POST.get(
                    "detect_common_features_map", False
                )
                detect_common_features_map_gbk = request.POST.get(
                    "detect_common_features_map_gbk", False
                )
                detect_common_features = (
                    True
                    if (
                        detect_common_features_map_dna or detect_common_features_map_gbk
                    )
                    else False
                )
                create_map_preview(obj, detect_common_features)
            except Exception:
                messages.error(
                    request,
                    "There was an error with detection of common features and/or saving of "
                    "the map preview",
                )

    def save_related(self, request, form, formsets, change):
        self.redirect_to_obj_page = False

        admin.ModelAdmin.save_related(self, request, form, formsets, change)

        obj = self.model.objects.get(pk=form.instance.id)

        # If a map is provided, automatically add those features
        # for which a corresponding sequence feature is present
        # in the database
        if self.clear_sequence_features:
            obj.sequence_features.clear()

        if self.rename_and_preview or "_redetect_sequence_features" in request.POST:
            unknown_feat_name_list = []
            try:
                feature_names = get_map_features(obj)
            except Exception:
                messages.error(request, "There was an error getting your map features")
                feature_names = []

            if not self.new_obj:
                obj.sequence_features.clear()

            if feature_names:
                sequence_features = SequenceFeature.objects.filter(
                    alias__label__in=feature_names
                ).distinct()
                aliases = list(sequence_features.values_list("alias__label", flat=True))
                obj.sequence_features.add(*list(sequence_features))
                unknown_feat_name_list = [
                    feat for feat in feature_names if feat not in aliases
                ]

                if unknown_feat_name_list:
                    self.redirect_to_obj_page = True
                    unknown_feat_name_list = str(unknown_feat_name_list)[1:-1].replace(
                        "'", ""
                    )
                    messages.warning(
                        request,
                        format_html(
                            "The following map features were not added to "
                            "<span style='background-color:rgba(0,0,0,0.1);'>Sequence Features</span>,"
                            " because they cannot be found in the database: "
                            "<span class='missing-formz-features' style='background-color:rgba(255,0,0,0.2)'>{}</span>. "
                            "You may want to add them manually yourself below.",
                            unknown_feat_name_list,
                        ),
                    )

        # For new records without map preview, delete first history record,
        # which contains the unformatted map name, and change the newer history
        # record's history_type from changed (~) to created (+). This gets rid of
        # a duplicate history record created when automatically generating a map name
        if self.new_obj and not self.rename_and_preview:
            obj.save()
            obj.history.last().delete()
            history_obj = obj.history.first()
            history_obj.history_type = "+"
            history_obj.save()
        else:
            obj.save_without_historical_record()

        super().save_history_fields(form, obj)

    def response_add(self, request, obj, post_url_continue=None):
        if self.redirect_to_obj_page:
            post = request.POST.copy()
            post.update({"_continue": ""})
            request.POST = post

        return super().response_add(request, obj, post_url_continue)

    def response_change(self, request, obj):
        if self.redirect_to_obj_page:
            post = request.POST.copy()
            post.update({"_continue": ""})
            request.POST = post

        return super().response_change(request, obj)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}

        obj = self.model.objects.get(pk=object_id)
        if (
            request.user == obj.created_by
            or request.user.groups.filter(name="Lab manager").exists()
            or request.user.is_pi
            or request.user.is_superuser
            or request.user.has_perm(
                f"{self.model._meta.app_label}.change_{self.model._meta.model_name}",
                obj,
            )
            or obj.created_by.groups.filter(name="Past member")
        ):
            extra_context.update({"show_redetect_save": True})

        return super().change_view(request, object_id, form_url, extra_context)

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj, change, **kwargs)
        if not obj and "formz_ecoli_strains" in form.base_fields:
            form.base_fields["formz_ecoli_strains"].initial = DEFAULT_ECOLI_STRAIN_IDS
        return form

    @admin.display(description="Map")
    def get_map_short_name(self, instance):
        if instance.map:
            ove_dna_preview = instance.map_ove_url
            ove_gbk_preview = instance.map_ove_url_gbk
            return mark_safe(
                f'<a class="magnific-popup-img-map" href="{instance.map_png.url}">png</a> | '
                f'<a href="{instance.map.url}">dna</a> <a class="magnific-popup-iframe-map-dna" href="{ove_dna_preview}">⊙</a> | '
                f'<a href="{instance.map_gbk.url}">gbk</a> <a class="magnific-popup-iframe-map-gbk" href="{ove_gbk_preview}">⊙</a>'
            )
        else:
            return ""
