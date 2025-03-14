from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.text import capfirst

from ordering.models import Order

from .actions import approve_all_new_orders, approve_records, notify_user_edits_required
from .search import (
    ActivityTypeFilter,
    ActivityUserFilter,
    ContentTypeFilter,
    MessageExistsFilter,
    MessageSentFilter,
)


class ApprovalAdmin(admin.ModelAdmin):
    list_display = (
        "magnificent_id",
        "titled_content_type",
        "record_link",
        "coloured_activity_type",
        "activity_user",
        "history_link",
        "message_exists",
        "message_sent",
        "edited",
    )
    list_display_links = None
    list_per_page = 50
    ordering = ["content_type", "-activity_type", "object_id"]
    actions = [approve_records, notify_user_edits_required, approve_all_new_orders]
    list_filter = (
        ContentTypeFilter,
        ActivityTypeFilter,
        ActivityUserFilter,
        MessageExistsFilter,
        MessageSentFilter,
        "edited",
    )

    def get_readonly_fields(self, request, obj=None):
        # Specifies which fields should be shown as read-only and when
        if obj:
            return [
                "content_type",
                "object_id",
                "content_object",
                "activity_type",
                "activity_user",
                "message_date_time",
                "edited",
                "created_date_time",
            ]
        else:
            return [
                "created_date_time",
            ]

    def changelist_view(self, request, extra_context=None):
        # Set queryset of action approve_all_new_orders
        if (
            "action" in request.POST
            and request.POST["action"] == "approve_all_new_orders"
        ):
            if not request.POST.getlist(admin.helpers.ACTION_CHECKBOX_NAME):
                post = request.POST.copy()
                for u in Order.objects.all():
                    post.update({admin.helpers.ACTION_CHECKBOX_NAME: str(u.id)})
                request._set_post(post)
        return super().changelist_view(request, extra_context=extra_context)

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        # If user is an approval manager but not a PI
        # show only collection items, not orders

        if (
            request.user.is_pi
            or request.user.is_superuser
            or request.user.groups.filter(name="Lab manager").exists()
        ):
            return qs
        elif request.user.groups.filter(name="Approval manager").exists():
            qs = qs.filter(content_type__app_label="collection").exclude(
                content_type__model="oligo"
            )
            approval_record_ids = []
            for approval_record in qs:
                obj = approval_record.content_object
                if request.user.id in obj.formz_projects.all().values_list(
                    "project_leader__id", flat=True
                ):
                    approval_record_ids.append(approval_record.id)
            return qs.filter(id__in=approval_record_ids)
        else:
            return qs

    @admin.display(description="Record")
    def record_link(self, instance):
        """Custom link to a record field for changelist_view"""

        url = reverse(
            f"admin:{instance.content_object._meta.app_label}_"
            f"{instance.content_object._meta.model_name}_change",
            args=(instance.content_object.id,),
        )
        record_name = str(instance.content_object)
        record_name = record_name[:50] + "..." if len(record_name) > 50 else record_name

        return mark_safe(
            '<a class="magnific-popup-iframe-original-object" href='
            f'"{url}?_to_field=id&_popup=1&_approval=1" target="_blank">{record_name}</a>'
        )

    @admin.display(description="History")
    def history_link(self, instance):
        """Custom link to a record's history field for changelist_view"""

        url = reverse(
            f"admin:{instance.content_object._meta.app_label}_"
            f"{instance.content_object._meta.model_name}_history",
            args=(instance.content_object.id,),
        )

        return mark_safe(
            '<a class="magnific-popup-iframe-history" href="'
            f'{url}?_to_field=id&_popup=1" target="_blank">History</a>'
        )

    @admin.display(description="Type", ordering="content_type")
    def titled_content_type(self, instance):
        """Custom link to a record's history field for changelist_view"""

        return capfirst(instance.content_type.model_class()._meta.verbose_name)

    @admin.display(description="Activity type", ordering="activity_type")
    def coloured_activity_type(self, instance):
        """Show created activity_type in red"""

        if instance.activity_type == "created":
            return mark_safe('<span class="activity-created"">Created</span>')
        elif instance.activity_type == "changed":
            return "Changed"

    @admin.display(description="Message sent?", boolean=True)
    def message_sent(self, instance):
        """Show whether a message has been sent or not"""

        if instance.message_date_time:
            return True
        else:
            return False

    @admin.display(description="Message?", boolean=True, ordering="message")
    def message_exists(self, instance):
        """Show whether a message exists"""

        return bool(instance.message)

    @admin.display(description="Approval ID")
    def magnificent_id(self, instance):
        """Show approval record link for magnificent popup"""

        url = reverse(
            f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_change",
            args=(instance.id,),
        )
        return mark_safe(
            f'<a class="magnific-popup-iframe-id" href="{url}'
            f'?_to_field=id&_popup=1" target="_blank">{instance.id}</a>'
        )
