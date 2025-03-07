import os

from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.html import format_html

from common.shared import (
    AddDocFileInlineMixin,
    DocFileInlineMixin,
)

from ..plasmid.admin import PlasmidAdmin
from ..shared.admin import (
    CollectionUserProtectionAdmin,
    CustomGuardedModelAdmin,
    SortAutocompleteResultsId,
    convert_map_gbk_to_dna,
    create_map_preview,
    formz_as_html,
)
from .actions import export_wormstrain, export_wormstrainallele
from .forms import WormStrainAdminForm, WormStrainAlleleAdminForm
from .models import (
    WormStrainAlleleDoc,
    WormStrainDoc,
    WormStrainGenotypingAssay,
)
from .search import WormStrainAlleleQLSchema, WormStrainQLSchema

MEDIA_ROOT = settings.MEDIA_ROOT
LAB_ABBREVIATION_FOR_FILES = getattr(settings, "LAB_ABBREVIATION_FOR_FILES", "")
WORM_ALLELE_LAB_ID_DEFAULT = getattr(settings, "WORM_ALLELE_LAB_ID_DEFAULT", "")
WORM_STRAIN_REGEX = getattr(settings, "WORM_STRAIN_REGEX", r"")
WORM_STRAIN_LAB_ID_DEFAULT = getattr(settings, "WORM_STRAIN_LAB_ID_DEFAULT", "")


class WormStrainGenotypingAssayInline(admin.TabularInline):
    """Inline to view existing worm genotyping assay"""

    model = WormStrainGenotypingAssay
    verbose_name = "genotyping assay"
    verbose_name_plural = "existing genotyping assays"
    extra = 0
    readonly_fields = ["locus_allele", "oligos"]

    def has_add_permission(self, request, obj):
        return False


class AddWormStrainGenotypingAssayInline(admin.TabularInline):
    """Inline to add new worm genotyping assays"""

    model = WormStrainGenotypingAssay
    verbose_name = "genotyping assay"
    verbose_name_plural = "new genotyping assays"
    extra = 0
    autocomplete_fields = ["oligos"]

    def has_change_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return self.model.objects.none()


class WormStrainDocInline(DocFileInlineMixin):
    """Inline to view existing worm strain documents"""

    model = WormStrainDoc


class WormStrainAddDocInline(AddDocFileInlineMixin):
    """Inline to add new worm strain documents"""

    model = WormStrainDoc


class WormStrainAdmin(
    SortAutocompleteResultsId,
    CustomGuardedModelAdmin,
    CollectionUserProtectionAdmin,
):
    list_display = (
        "id",
        "name",
        "chromosomal_genotype",
        "stocked",
        "created_by",
        "approval",
    )
    list_display_links = ("id",)
    actions = [export_wormstrain, formz_as_html]
    form = WormStrainAdminForm
    djangoql_schema = WormStrainQLSchema
    search_fields = ["id", "name"]
    show_plasmids_in_model = True
    autocomplete_fields = [
        "parent_1",
        "parent_2",
        "formz_projects",
        "formz_gentech_methods",
        "formz_elements",
        "alleles",
        "integrated_dna_plasmids",
        "integrated_dna_oligos",
    ]
    inlines = [
        WormStrainGenotypingAssayInline,
        AddWormStrainGenotypingAssayInline,
        WormStrainDocInline,
        WormStrainAddDocInline,
    ]
    change_form_template = "admin/collection/change_form.html"
    obj_specific_fields = [
        "name",
        "chromosomal_genotype",
        "parent_1",
        "parent_2",
        "construction",
        "outcrossed",
        "growth_conditions",
        "organism",
        "selection",
        "phenotype",
        "received_from",
        "us_e",
        "note",
        "reference",
        "at_cgc",
        "alleles",
        "integrated_dna_plasmids",
        "integrated_dna_oligos",
        "location_freezer1",
        "location_freezer2",
        "location_backup",
        "formz_projects",
        "formz_risk_group",
        "formz_gentech_methods",
        "formz_elements",
        "destroyed_date",
    ]
    obj_unmodifiable_fields = [
        "created_date_time",
        "created_approval_by_pi",
        "last_changed_date_time",
        "last_changed_approval_by_pi",
        "created_by",
    ]
    add_view_fieldsets = [
        [
            None,
            {"fields": obj_specific_fields[:15]},
        ],
        [
            "Integrated DNA",
            {
                "fields": obj_specific_fields[15:18],
            },
        ],
        [
            "Location",
            {"fields": obj_specific_fields[18:21]},
        ],
        [
            "FormZ",
            {"fields": obj_specific_fields[21:]},
        ],
    ]
    change_view_fieldsets = [
        [
            None,
            {"fields": obj_specific_fields[:15] + obj_unmodifiable_fields},
        ],
        [
            "Integrated DNA",
            {
                "fields": obj_specific_fields[15:18],
            },
        ],
        [
            "Location",
            {"fields": obj_specific_fields[18:21]},
        ],
        [
            "FormZ",
            {"classes": (("collapse",)), "fields": obj_specific_fields[21:]},
        ],
    ]
    m2m_save_ignore_fields = ["history_genotyping_oligos"]

    @admin.display(description="Stocked", boolean=True)
    def stocked(self, instance):
        if any(
            len(s.strip()) > 0
            for s in [
                instance.location_freezer1,
                instance.location_freezer1,
                instance.location_backup,
            ]
        ):
            return True
        return False

    def save_related(self, request, form, formsets, change):
        obj, history_obj = super().save_related(request, form, formsets, change)

        obj.history_genotyping_oligos = (
            sorted(
                list(
                    set(
                        obj.wormstraingenotypingassay_set.all().values_list(
                            "oligos", flat=True
                        )
                    )
                )
            )
            if obj.wormstraingenotypingassay_set.exists()
            else []
        )
        obj.save_without_historical_record()

        history_obj.history_genotyping_oligos = obj.history_genotyping_oligos
        history_obj.save()

    def get_inline_instances(self, request, obj=None):
        inline_instances = super().get_inline_instances(request, obj)
        filtered_inline_instances = []

        # New objects
        if not obj:
            for inline in inline_instances:
                if inline.verbose_name_plural == "existing genotyping assays":
                    filtered_inline_instances.append(inline)
                else:
                    if not request.user.groups.filter(name="Guest").exists():
                        filtered_inline_instances.append(inline)

        # Existing objects
        else:
            for inline in inline_instances:
                # Always show existing docs
                if inline.verbose_name_plural == "Existing docs":
                    filtered_inline_instances.append(inline)
                else:
                    # Do not allow guests to add docs, ever
                    if not request.user.groups.filter(name="Guest").exists():
                        filtered_inline_instances.append(inline)

        return filtered_inline_instances

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        # Try to get the latest strain ID from name
        if (
            not obj
            and WORM_STRAIN_REGEX
            and WORM_STRAIN_LAB_ID_DEFAULT
            and "name" in form.base_fields
        ):
            strain_greatest_id = (
                self.model.objects.filter(name__iregex=WORM_STRAIN_REGEX)
                .extra(
                    select={
                        "strain_id": f"CAST((REGEXP_MATCH(name, '{WORM_STRAIN_REGEX}'))[1] AS INTEGER)"
                    }
                )
                .order_by("-strain_id")
                .first()
            )
            if strain_greatest_id:
                form.base_fields[
                    "name"
                ].initial = (
                    f"{WORM_STRAIN_LAB_ID_DEFAULT}{strain_greatest_id.strain_id + 1}"
                )
        return form

    def add_view(self, request, form_url="", extra_context=None):
        obj_unmodifiable_fields = self.obj_unmodifiable_fields.copy()
        add_view_main_fields = self.add_view_fieldsets[0][1]["fields"].copy()
        if (
            request.user.is_superuser
            or request.user.groups.filter(name="Lab manager").exists()
        ):
            obj_unmodifiable_fields = [
                x for x in obj_unmodifiable_fields if x != "created_by"
            ]
            add_view_main_fields = (
                add_view_main_fields + ["created_by"]
                if "created_by" not in add_view_main_fields
                else add_view_main_fields
            )
        else:
            obj_unmodifiable_fields = set(obj_unmodifiable_fields)
            obj_unmodifiable_fields.add("created_by")
            obj_unmodifiable_fields = list(obj_unmodifiable_fields)
            add_view_main_fields = [
                x for x in add_view_main_fields if x != "created_by"
            ]

        self.obj_unmodifiable_fields = obj_unmodifiable_fields
        self.add_view_fieldsets[0][1]["fields"] = add_view_main_fields

        return super().add_view(request, form_url, extra_context)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        obj_unmodifiable_fields = set(self.obj_unmodifiable_fields)
        obj_unmodifiable_fields.add("created_by")
        self.obj_unmodifiable_fields = list(list(obj_unmodifiable_fields))

        return super().change_view(request, object_id, form_url, extra_context)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        try:
            request.resolver_match.args[0]
        except Exception:
            # Exclude certain users from the 'Created by' field in the order form
            if db_field.name == "created_by":
                if (
                    request.user.is_superuser
                    or request.user.groups.filter(name="Lab manager").exists()
                ):
                    kwargs["queryset"] = User.objects.exclude(
                        username__in=["admin", "guest", "AnonymousUser"]
                    ).order_by("last_name")
                # kwargs["initial"] = request.user.id # disable this for now

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class WormStrainAlleleDocInline(DocFileInlineMixin):
    """Inline to view existing worm strain documents"""

    model = WormStrainAlleleDoc


class WormStrainAlleleAddDocInline(AddDocFileInlineMixin):
    """Inline to add new worm strain documents"""

    model = WormStrainAlleleDoc


class WormStrainAlleleAdmin(PlasmidAdmin):
    list_display = (
        "id",
        "typ_e",
        "description",
        "get_map_short_name",
        "created_by",
    )
    list_display_links = ("id",)
    djangoql_schema = WormStrainAlleleQLSchema
    actions = [export_wormstrainallele]
    search_fields = ["id", "mutation", "transgene"]
    autocomplete_fields = [
        "formz_elements",
        "made_by_method",
        "reference_strain",
        "transgene_plasmids",
        "made_with_plasmids",
    ]
    form = WormStrainAlleleAdminForm
    inlines = [WormStrainAlleleDocInline, WormStrainAlleleAddDocInline]
    allele_type = ""
    show_formz = False
    show_plasmids_in_model = True
    obj_specific_fields = [
        "lab_identifier",
        "typ_e",
        "transgene",
        "transgene_position",
        "transgene_plasmids",
        "mutation",
        "mutation_type",
        "mutation_position",
        "reference_strain",
        "made_by_method",
        "made_by_person",
        "made_with_plasmids",
        "notes",
        "map",
        "map_png",
        "map_gbk",
        "formz_elements",
    ]
    obj_unmodifiable_fields = [
        "created_date_time",
        "last_changed_date_time",
        "created_by",
    ]
    set_readonly_fields = [
        "map_png",
    ]

    add_form_template = "admin/collection/wormstrainallele/add_form.html"
    change_form_template = "admin/collection/wormstrainallele/change_form.html"

    def has_module_permission(self, request):
        return False

    def save_model(self, request, obj, form, change):
        rename_and_preview = False
        self.rename_and_preview = False
        new_obj = False
        self.new_obj = False
        self.clear_formz_elements = False
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

            # If an object is 'Saved as new', clear all form Z elements
            if "_saveasnew" in request.POST and (obj.map or obj.map_gbk):
                self.clear_formz_elements = True

            # Check if a map is present and if so trigger functions to create a
            # map preview and delete the resulting duplicate history record
            if obj.map:
                rename_and_preview = True
                self.rename_and_preview = True
            elif obj.map_gbk:
                rename_and_preview = True
                self.rename_and_preview = True
                convert_map_to_dna = True

        else:
            # Check if the request's user can change the object, if not raise PermissionDenied

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
                    self.clear_formz_elements = True
                    obj.save()

            else:
                obj.save()

        # Rename map
        if rename_and_preview:
            timestamp = timezone.now().strftime("%Y%m%d_%H%M%S_%f")
            new_file_name = f"{self.model._model_abbreviation}{LAB_ABBREVIATION_FOR_FILES}{obj.id}_{timestamp}"

            new_dna_file_name = os.path.join(
                self.model._model_upload_to, "dna/", new_file_name + ".dna"
            )
            new_gbk_file_name = os.path.join(
                self.model._model_upload_to, "gbk/", new_file_name + ".gbk"
            )
            new_png_file_name = os.path.join(
                self.model._model_upload_to, "png/", new_file_name + ".png"
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
                        request, "There was an error with converting the map to .gbk."
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
                create_map_preview(
                    obj, detect_common_features, prefix=obj.lab_identifier
                )
            except Exception:
                messages.error(
                    request,
                    "There was an error detecting common features and/or saving the map preview",
                )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        allele_type = ""
        required_fields = []

        if (obj and obj.typ_e == "t") or self.allele_type == "t":
            allele_type = "t"
            required_fields = ["transgene", "transgene_position", "transgene_plasmids"]
        elif (obj and obj.typ_e == "m") or self.allele_type == "m":
            allele_type = "m"
            required_fields = ["mutation", "mutation_type", "mutation_position"]

        if "typ_e" in form.base_fields:
            form.base_fields["typ_e"].initial = allele_type
            form.base_fields["typ_e"].disabled = True
        if self.can_change:
            [setattr(form.base_fields[f], "required", True) for f in required_fields]

        if (
            not obj
            and WORM_ALLELE_LAB_ID_DEFAULT
            and "lab_identifier" in form.base_fields
        ):
            form.base_fields["lab_identifier"].initial = WORM_ALLELE_LAB_ID_DEFAULT

        return form

    def add_view(self, request, form_url="", extra_context=None):
        fields = self.obj_specific_fields.copy()
        self.allele_type = request.GET.get("allele_type")
        obj_unmodifiable_fields = self.obj_unmodifiable_fields.copy()

        if (
            request.user.is_superuser
            or request.user.groups.filter(name="Lab manager").exists()
        ):
            obj_unmodifiable_fields = [
                x for x in obj_unmodifiable_fields if x != "created_by"
            ]
            fields = fields + ["created_by"] if "created_by" not in fields else fields
        else:
            obj_unmodifiable_fields = set(obj_unmodifiable_fields)
            obj_unmodifiable_fields.add("created_by")
            obj_unmodifiable_fields = list(obj_unmodifiable_fields)
            fields = [x for x in fields if x != "created_by"]

        self.obj_unmodifiable_fields = obj_unmodifiable_fields

        if self.allele_type == "t":
            fields = [f for f in fields if not f.startswith("mutation")]
        elif self.allele_type == "m":
            fields = [f for f in fields if not f.startswith("transgene")]
        else:
            fields = []

        self.add_view_fieldsets = [
            [
                None,
                {"fields": fields},
            ],
        ]

        return super().add_view(request, form_url, extra_context)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        obj = self.model.objects.get(pk=object_id)
        fields = self.obj_specific_fields.copy()

        if obj.typ_e == "t":
            fields = [f for f in fields if not f.startswith("mutation")]
        elif obj.typ_e == "m":
            fields = [f for f in fields if not f.startswith("transgene")]

        obj_unmodifiable_fields = set(self.obj_unmodifiable_fields)
        obj_unmodifiable_fields.add("created_by")
        self.obj_unmodifiable_fields = list(list(obj_unmodifiable_fields))

        self.change_view_fieldsets = [
            [
                None,
                {"fields": fields + self.obj_unmodifiable_fields},
            ],
        ]

        return super().change_view(request, object_id, form_url, extra_context)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        try:
            request.resolver_match.args[0]
        except Exception:
            # Exclude certain users from the 'Created by' field in the order form
            if db_field.name == "created_by":
                if (
                    request.user.is_superuser
                    or request.user.groups.filter(name="Lab manager").exists()
                ):
                    kwargs["queryset"] = User.objects.exclude(
                        username__in=["admin", "guest", "AnonymousUser"]
                    ).order_by("last_name")
                # kwargs["initial"] = request.user.id # disable this for now

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.display(description="Description")
    def description(self, instance):
        return format_html(
            "<b>{}{}</b> - {}", instance.lab_identifier, instance.id, instance.name
        )
