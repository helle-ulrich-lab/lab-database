from django.contrib import admin
from django.utils import timezone

from .models import Oligo, OligoDoc
from common.shared import (
    AddDocFileInlineMixin,
    DocFileInlineMixin,
)
from formz.models import FormZBaseElement

from ..shared.admin import (
    CollectionUserProtectionAdmin,
    rename_info_sheet_save_obj_update_history,
)
from .actions import export_oligo
from .forms import OligoAdminForm
from .search import OligoDjangoQLSearchMixin, OligoQLSchema


class OligoDocInline(DocFileInlineMixin):
    """Inline to view existing Oligo documents"""

    model = OligoDoc


class OligoAddDocInline(AddDocFileInlineMixin):
    """Inline to add new Oligo documents"""

    model = OligoDoc


class OligoAdmin(
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
    form = OligoAdminForm
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
