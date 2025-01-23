import os

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone
from django.utils.html import format_html
from djangoql.schema import DjangoQLSchema, IntField, StrField
from import_export import resources
from import_export.fields import Field

from collection.admin.plasmid import PlasmidPage
from collection.admin.shared import (
    CollectionUserProtectionAdmin,
    CustomGuardedModelAdmin,
    FieldCreated,
    FieldFormZBaseElement,
    FieldFormZProject,
    FieldLastChanged,
    FieldParent1,
    FieldParent2,
    FieldUse,
    FormTwoMapChangeCheck,
    OptionalChoiceField,
    SortAutocompleteResultsId,
    convert_map_gbk_to_dna,
    create_map_preview,
    formz_as_html,
)
from collection.models import (
    Oligo,
    Plasmid,
    WormStrain,
    WormStrainAllele,
    WormStrainAlleleDoc,
    WormStrainDoc,
    WormStrainGenotypingAssay,
)
from common.shared import (
    AddDocFileInlineMixin,
    DocFileInlineMixin,
    SearchFieldOptLastname,
    SearchFieldOptUsername,
    export_objects,
)
from formz.models import FormZBaseElement, FormZProject, GenTechMethod

MEDIA_ROOT = settings.MEDIA_ROOT
LAB_ABBREVIATION_FOR_FILES = getattr(settings, "LAB_ABBREVIATION_FOR_FILES", "")
WORM_ALLELE_LAB_IDS = getattr(settings, "WORM_ALLELE_LAB_IDS", [])
WORM_ALLELE_LAB_ID_DEFAULT = getattr(settings, "WORM_ALLELE_LAB_ID_DEFAULT", "")
WORM_STRAIN_REGEX = getattr(settings, "WORM_STRAIN_REGEX", r"")
WORM_STRAIN_LAB_ID_DEFAULT = getattr(settings, "WORM_STRAIN_LAB_ID_DEFAULT", "")


class SearchFieldOptUsernameWormStrain(SearchFieldOptUsername):
    id_list = WormStrain.objects.all().values_list("created_by", flat=True).distinct()


class SearchFieldOptLastnameWormStrain(SearchFieldOptLastname):
    id_list = WormStrain.objects.all().values_list("created_by", flat=True).distinct()


class FieldAlleleName(StrField):
    model = WormStrainAllele
    name = "allele_name"
    suggest_options = True

    def get_options(self, search):
        if len(search) < 3:
            return ["Type 3 or more characters to see suggestions"]

        qs = self.model.objects.filter(
            Q(transgene__icontains=search) | Q(mutation__icontains=search)
        )
        return [a.name for a in qs]

    def get_lookup(self, path, operator, value):
        op, invert = self.get_operator(operator)
        value = self.get_lookup_value(value)

        q = Q(**{f"alleles__transgene{op}": value}) | Q(
            **{f"alleles__mutation{op}": value}
        )

        return ~q if invert else q


class FieldAlleleId(IntField):
    model = WormStrainAllele
    name = "allele_id"
    suggest_options = False

    def get_lookup_name(self):
        return "alleles__id"


class WormStrainQLSchema(DjangoQLSchema):
    """Customize search functionality"""

    include = (WormStrain, User)  # Include only the relevant models to be searched

    def get_fields(self, model):
        """Define fields that can be searched"""

        if model == WormStrain:
            return [
                "id",
                "name",
                "chromosomal_genotype",
                FieldParent1(),
                FieldParent2(),
                "construction",
                "outcrossed",
                "growth_conditions",
                "organism",
                "selection",
                "phenotype",
                "received_from",
                FieldUse(),
                "note",
                "reference",
                "at_cgc",
                "location_freezer1",
                "location_freezer2",
                "location_backup",
                FieldAlleleId(),
                FieldAlleleName(),
                "created_by",
                FieldCreated(),
                FieldLastChanged(),
                FieldFormZProject(),
            ]
        elif model == User:
            return [
                SearchFieldOptUsernameWormStrain(),
                SearchFieldOptLastnameWormStrain(),
            ]
        return super().get_fields(model)


class WormStrainExportResource(resources.ModelResource):
    """Defines a custom export resource class for WormStrain"""

    primers_for_genotyping = Field()

    def dehydrate_primers_for_genotyping(self, strain):
        return str(strain.history_genotyping_oligos)[1:-1]

    class Meta:
        model = WormStrain
        fields = (
            "id",
            "name",
            "chromosomal_genotype",
            "parent_1",
            "parent_2",
            "construction",
            "outcrossed",
            "growth_conditions",
            "organism",
            "integrated_dna_plasmids",
            "integrated_dna_oligos",
            "selection",
            "phenotype",
            "received_from",
            "us_e",
            "note",
            "reference",
            "at_cgc",
            "location_freezer1",
            "location_freezer2",
            "location_backup",
            "primers_for_genotyping",
            "created_date_time",
            "created_by__username",
        )
        export_order = fields


@admin.action(description="Export selected strains")
def export_wormstrain(modeladmin, request, queryset):
    """Export WormStrain"""

    export_data = WormStrainExportResource().export(queryset)
    return export_objects(request, queryset, export_data)


class WormStrainForm(forms.ModelForm):
    class Meta:
        model = WormStrain
        fields = "__all__"

    def clean_name(self):
        """Check if name is unique before saving"""

        if not self.instance.pk:
            qs = self._meta.model.objects.filter(name=self.cleaned_data["name"])
            if qs.exists():
                raise forms.ValidationError("Strain with this name already exists.")
            else:
                return self.cleaned_data["name"]
        else:
            return self.cleaned_data["name"]


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


class WormStrainPage(
    SortAutocompleteResultsId,
    CustomGuardedModelAdmin,
    CollectionUserProtectionAdmin,
):
    list_display = ("id", "name", "chromosomal_genotype", "created_by", "approval")
    list_display_links = ("id",)
    actions = [export_wormstrain, formz_as_html]
    form = WormStrainForm
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
    history_array_fields = {
        "history_integrated_dna_plasmids": Plasmid,
        "history_integrated_dna_oligos": Oligo,
        "history_formz_projects": FormZProject,
        "history_formz_gentech_methods": GenTechMethod,
        "history_formz_elements": FormZBaseElement,
        "history_genotyping_oligos": Oligo,
        "history_documents": WormStrainDoc,
        "history_alleles": WormStrainAllele,
    }

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


class SearchFieldOptUsernameWormStrainAllele(SearchFieldOptUsername):
    id_list = (
        WormStrainAllele.objects.all().values_list("created_by", flat=True).distinct()
    )


class SearchFieldOptLastnameWormStrainAllele(SearchFieldOptLastname):
    id_list = (
        WormStrainAllele.objects.all().values_list("created_by", flat=True).distinct()
    )


class FieldFormZBaseElementWormStrainAllele(FieldFormZBaseElement):
    model = WormStrainAllele


class FieldTransgenePlasmidsWormStrainAllele(IntField):
    name = "transgene_plasmids_id"

    def get_lookup_name(self):
        return "transgene_plasmids__id"


class FieldMadeWithPlasmidsWormStrainAllele(IntField):
    name = "made_with_plasmids_id"

    def get_lookup_name(self):
        return "made_with_plasmids__id"


class WormStrainAlleleQLSchema(DjangoQLSchema):
    """Customize search functionality"""

    include = (
        WormStrainAllele,
        User,
    )  # Include only the relevant models to be searched

    def get_fields(self, model):
        """Define fields that can be searched"""

        if model == self.include[0]:
            return [
                "id",
                "lab_identifier",
                "typ_e",
                "transgene",
                "transgene_position",
                FieldTransgenePlasmidsWormStrainAllele(),
                "mutation",
                "mutation_type",
                "mutation_position",
                "reference_strain",
                "made_by_method",
                "made_by_person",
                FieldMadeWithPlasmidsWormStrainAllele(),
                "notes",
                "created_by",
                FieldCreated(),
                FieldLastChanged(),
                FieldFormZBaseElement(),
            ]
        elif model == self.include[1]:
            return [
                SearchFieldOptUsernameWormStrainAllele(),
                SearchFieldOptLastnameWormStrainAllele(),
            ]
        return super().get_fields(model)


class WormStrainAlleleExportResource(resources.ModelResource):
    """Defines a custom export resource class for WormStrainAllele"""

    made_by_method = Field()
    type = Field()

    def dehydrate_made_by_method(self, strain):
        return strain.made_by_method.english_name

    def dehydrate_type(self, strain):
        return strain.get_typ_e_display()

    class Meta:
        model = WormStrainAllele
        fields = (
            "id",
            "lab_identifier",
            "type",
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
            "created_date_time",
            "created_by__username",
        )
        export_order = fields


@admin.action(description="Export selected worm strain alleles")
def export_wormstrainallele(modeladmin, request, queryset):
    """Export WormStrainAllele"""

    export_data = WormStrainAlleleExportResource().export(queryset)
    return export_objects(request, queryset, export_data)


class WormStrainAlleleDocInline(DocFileInlineMixin):
    """Inline to view existing worm strain documents"""

    model = WormStrainAlleleDoc


class WormStrainAlleleAddDocInline(AddDocFileInlineMixin):
    """Inline to add new worm strain documents"""

    model = WormStrainAlleleDoc


class WormStrainAlleleForm(FormTwoMapChangeCheck, forms.ModelForm):
    if WORM_ALLELE_LAB_IDS:
        lab_identifier = OptionalChoiceField(
            choices=WORM_ALLELE_LAB_IDS,
        )


class WormStrainAllelePage(PlasmidPage):
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
    form = WormStrainAlleleForm
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
    history_array_fields = {
        "history_formz_elements": FormZBaseElement,
        "history_made_with_plasmids": Plasmid,
        "history_transgene_plasmids": Plasmid,
        "history_documents": WormStrainAlleleDoc,
    }

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

        self.change_view_fieldsets = [
            [
                None,
                {"fields": fields + self.obj_unmodifiable_fields},
            ],
        ]

        return super().change_view(request, object_id, form_url, extra_context)

    @admin.display(description="Description")
    def description(self, instance):
        return format_html(
            "<b>{}{}</b> - {}", instance.lab_identifier, instance.id, instance.name
        )
