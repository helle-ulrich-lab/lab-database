from django import forms
from django.contrib import admin, messages
from django.contrib.auth.models import User
from django.core.exceptions import FieldError, ValidationError
from django.db import DataError, models
from django.db.models.functions import Collate
from django.utils import timezone
from djangoql.admin import DjangoQLSearchMixin
from djangoql.exceptions import DjangoQLError
from djangoql.parser import DjangoQLParser
from djangoql.queryset import build_filter
from djangoql.schema import DjangoQLSchema, StrField
from import_export import resources

from collection.admin.shared import (
    CollectionUserProtectionAdmin,
    FieldCreated,
    FieldLastChanged,
    FieldUse,
    rename_info_sheet_save_obj_update_history,
)
from collection.models import Oligo, OligoDoc
from common.shared import (
    AddDocFileInlineMixin,
    DocFileInlineMixin,
    SearchFieldOptLastname,
    SearchFieldOptUsername,
    export_objects,
)
from formz.models import FormZBaseElement


class SearchFieldOptUsernameOligo(SearchFieldOptUsername):
    id_list = Oligo.objects.all().values_list("created_by", flat=True).distinct()


class SearchFieldOptLastnameOligo(SearchFieldOptLastname):
    id_list = Oligo.objects.all().values_list("created_by", flat=True).distinct()


class OligoSequence(StrField):
    name = "sequence"

    def get_lookup(self, path, operator, value):
        """Override parent's method to include deterministic
        collation flag to lookup for sequence"""

        search = "__".join(path + [self.get_lookup_name()])
        search = (
            search.replace("sequence", "sequence_deterministic")
            if "sequence" in search
            else search
        )
        op, invert = self.get_operator(operator)
        q = models.Q(**{f"{search}{op}": self.get_lookup_value(value)})
        return ~q if invert else q


class OligoQLSchema(DjangoQLSchema):
    """Customize search functionality"""

    include = (Oligo, User)

    def get_fields(self, model):
        """Define fields that can be searched"""

        if model == Oligo:
            return [
                "id",
                "name",
                OligoSequence(),
                "length",
                FieldUse(),
                "gene",
                "restriction_site",
                "description",
                "comment",
                "created_by",
                FieldCreated(),
                FieldLastChanged(),
            ]
        elif model == User:
            return [SearchFieldOptUsernameOligo(), SearchFieldOptLastnameOligo()]
        return super().get_fields(model)


class OligoExportResource(resources.ModelResource):
    """Defines a custom export resource class for Oligo"""

    class Meta:
        model = Oligo
        fields = (
            "id",
            "name",
            "sequence",
            "us_e",
            "gene",
            "restriction_site",
            "description",
            "comment",
            "created_date_time",
            "created_by__username",
        )
        export_order = fields


@admin.action(description="Export selected oligos")
def export_oligo(modeladmin, request, queryset):
    """Export Oligo"""

    export_data = OligoExportResource().export(queryset)
    return export_objects(request, queryset, export_data)


class OligoForm(forms.ModelForm):
    class Meta:
        model = Oligo
        fields = "__all__"

    def clean_sequence(self):
        """Check if sequence is unique before saving"""

        sequence = self.cleaned_data["sequence"]
        qs = self._meta.model.objects.filter(sequence=sequence)

        if not self.instance.pk:
            if qs.exists():
                raise forms.ValidationError("Oligo with this Sequence already exists.")
        else:
            if qs.exclude(id=self.instance.pk).exists():
                raise forms.ValidationError("Oligo with this Sequence already exists.")

        return sequence

    def clean_name(self):
        """Check if name is unique before saving"""

        name = self.cleaned_data["name"]
        qs = self._meta.model.objects.filter(name=name)

        if not self.instance.pk:
            if qs.exists():
                raise forms.ValidationError("Oligo with this Name already exists.")
        else:
            if qs.exclude(id=self.instance.pk).exists():
                raise forms.ValidationError("Oligo with this Name already exists.")

        return name


class OligoDjangoQLSearchMixin(DjangoQLSearchMixin):
    def get_search_results(self, request, queryset, search_term):
        """
        Filter sequence using a non-deterministic collaction
        """

        def apply_search(queryset, search, schema=None):
            ast = DjangoQLParser().parse(search)
            schema = schema or DjangoQLSchema
            schema_instance = schema(queryset.model)
            schema_instance.validate(ast)
            filter_params = build_filter(ast, schema_instance)
            if any(n[0].startswith("sequence") for n in filter_params.deconstruct()[1]):
                return queryset.annotate(
                    sequence_deterministic=Collate("sequence", "und-x-icu")
                ).filter(filter_params)
            return queryset.filter(filter_params)

        if self.search_mode_toggle_enabled() and not self.djangoql_search_enabled(
            request
        ):
            return super(DjangoQLSearchMixin, self).get_search_results(
                request=request,
                queryset=queryset,
                search_term=search_term,
            )
        use_distinct = False
        if not search_term:
            return queryset, use_distinct

        try:
            qs = apply_search(queryset, search_term, self.djangoql_schema)
        except (DjangoQLError, ValueError, FieldError, ValidationError) as e:
            msg = self.djangoql_error_message(e)
            messages.add_message(request, messages.WARNING, msg)
            qs = queryset.none()
        else:
            # Hack to handle 'inet' comparison errors in Postgres. If you
            # know a better way to check for such an error, please submit a PR.
            try:
                # Django >= 2.1 has built-in .explain() method
                explain = getattr(qs, "explain", None)
                if callable(explain):
                    explain()
                else:
                    list(qs[:1])
            except DataError as e:
                if "inet" not in str(e):
                    raise
                msg = self.djangoql_error_message(e)
                messages.add_message(request, messages.WARNING, msg)
                qs = queryset.none()

        return qs, use_distinct


class OligoDocInline(DocFileInlineMixin):
    """Inline to view existing Oligo documents"""

    model = OligoDoc


class OligoAddDocInline(AddDocFileInlineMixin):
    """Inline to add new Oligo documents"""

    model = OligoDoc


class OligoPage(
    OligoDjangoQLSearchMixin,
    CollectionUserProtectionAdmin,
):
    list_display = (
        "id",
        "name",
        "get_oligo_short_sequence",
        "restriction_site",
        "created_by",
        "approval",
    )
    list_display_links = ("id",)
    djangoql_schema = OligoQLSchema
    actions = [export_oligo]
    search_fields = ["id", "name"]
    autocomplete_fields = ["formz_elements"]
    form = OligoForm
    inlines = [OligoDocInline, OligoAddDocInline]
    show_formz = False
    clone_ignore_fields = [
        "info_sheet",
    ]
    obj_specific_fields = [
        "name",
        "sequence",
        "us_e",
        "gene",
        "restriction_site",
        "description",
        "comment",
        "info_sheet",
        "formz_elements",
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
            {"fields": obj_specific_fields},
        ],
    ]
    change_view_fieldsets = [
        [
            None,
            {"fields": obj_specific_fields + obj_unmodifiable_fields},
        ],
    ]
    history_array_fields = {
        "history_formz_elements": FormZBaseElement,
        "history_documents": OligoDoc,
    }

    def save_model(self, request, obj, form, change):
        rename_doc = False
        new_obj = False

        if obj.pk is None:
            obj.id = (
                self.model.objects.order_by("-id").first().id + 1
                if self.model.objects.exists()
                else 1
            )
            obj.created_by = request.user
            if obj.info_sheet:
                rename_doc = True
                new_obj = True
            obj.save()

            # If the request's user is the principal investigator, approve
            # the record right away. If not, create an approval record
            if request.user.labuser.is_principal_investigator:
                original_last_changed_date_time = obj.last_changed_date_time
                obj.created_approval_by_pi = True
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
                if not obj.approval.all():
                    original_last_changed_date_time = obj.last_changed_date_time
                    obj.approval.create(
                        activity_type="changed", activity_user=obj.created_by
                    )
                    obj.last_changed_approval_by_pi = False
                    obj.save_without_historical_record()
                    Oligo.objects.filter(id=obj.pk).update(
                        last_changed_date_time=original_last_changed_date_time
                    )
                return

            # Approve right away if the request's user is the PI.
            # If not, create an approval record
            if request.user.labuser.is_principal_investigator:
                obj.last_changed_approval_by_pi = True
                if not obj.created_approval_by_pi:
                    obj.created_approval_by_pi = True
                obj.approval_by_pi_date_time = timezone.now()

                if obj.approval.all().exists():
                    approval_records = obj.approval.all()
                    approval_records.delete()
            else:
                obj.last_changed_approval_by_pi = False

                # If an approval record for this object does not exist, create one
                if not obj.approval.all().exists():
                    obj.approval.create(
                        activity_type="changed", activity_user=request.user
                    )
                else:
                    # If an approval record for this object exists, check if a message
                    # was sent. If so, update the approval record's edited field
                    approval_obj = obj.approval.all().latest("message_date_time")
                    if approval_obj.message_date_time:
                        if obj.last_changed_date_time > approval_obj.message_date_time:
                            approval_obj.edited = True
                            approval_obj.save()

            saved_obj = self.model.objects.get(pk=obj.pk)
            if obj.info_sheet and obj.info_sheet != saved_obj.info_sheet:
                rename_doc = True
                obj.save_without_historical_record()
            else:
                obj.save()

        # Rename info_sheet
        if rename_doc:
            rename_info_sheet_save_obj_update_history(obj, new_obj)

    @admin.display(description="Sequence")
    def get_oligo_short_sequence(self, instance):
        if instance.sequence:
            if len(instance.sequence) <= 75:
                return instance.sequence
            else:
                return instance.sequence[0:75] + "..."
