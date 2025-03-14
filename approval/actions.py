from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.http import HttpResponseRedirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from ordering.models import Order

from .models import Approval

User = get_user_model()
SITE_TITLE = getattr(settings, "SITE_TITLE", "Lab DB")
SERVER_EMAIL_ADDRESS = getattr(settings, "SERVER_EMAIL_ADDRESS", "email@example.com")


@admin.action(description="Approve records")
def approve_records(modeladmin, request, queryset):
    """Approve records"""

    def approve_collection_model(approval):
        """Approve a collection record that is not an oligo"""

        obj = approval.content_object
        if request.user.id in obj.formz_projects.all().values_list(
            "project_leader__id", flat=True
        ):
            model = obj._meta.model
            if approval.activity_type == "created":
                if not obj.last_changed_approval_by_pi:
                    model.objects.filter(id=obj.id).update(
                        created_approval_by_pi=True,
                        last_changed_approval_by_pi=True,
                        approval_by_pi_date_time=now,
                        approval_user=request.user,
                    )
                else:
                    model.objects.filter(id=obj.id).update(
                        created_approval_by_pi=True,
                        approval_by_pi_date_time=now,
                        approval_user=request.user,
                    )
            elif approval.activity_type == "changed":
                model.objects.filter(id=obj.id).update(
                    last_changed_approval_by_pi=True,
                    approval_by_pi_date_time=now,
                    approval_user=request.user,
                )
            approval.delete()
            msg["success_message"] = True
        else:
            msg["warning_message"] = True

    def approve_oligo(oligo_approval_record):
        """Approve an oligo"""

        oligo = oligo_approval_record.content_object
        # New oligos
        if oligo_approval_record.activity_type == "created":
            if not oligo.last_changed_approval_by_pi:
                oligo._meta.model.objects.filter(id=oligo.id).update(
                    created_approval_by_pi=True,
                    last_changed_approval_by_pi=True,
                    approval_by_pi_date_time=now,
                )
            else:
                oligo._meta.model.objects.filter(id=oligo.id).update(
                    created_approval_by_pi=True,
                    approval_by_pi_date_time=now,
                )
        # Existing changed oligos
        elif oligo_approval_record.activity_type == "changed":
            oligo._meta.model.objects.filter(id=oligo.id).update(
                last_changed_approval_by_pi=True,
                approval_by_pi_date_time=now,
            )

    now = timezone.now()
    msg = {"success_message": False, "warning_message": False}

    # Collection records
    collection_approvals = queryset.filter(content_type__app_label="collection")

    # Collection records, except oligos
    [
        approve_collection_model(approval)
        for approval in collection_approvals.exclude(content_type__model="oligo")
    ]

    # Oligos
    if request.user.is_pi:
        oligo_approvals = collection_approvals.filter(content_type__model="oligo")
        if oligo_approvals.exists():
            [approve_oligo(oligo_approval) for oligo_approval in oligo_approvals]
            oligo_approvals.delete()
            msg["success_message"] = True
    else:
        messages.error(request, "You are not allowed to approve oligos")

    # Orders
    if request.user.is_pi:
        order_approval_records = queryset.filter(content_type__app_label="ordering")
        if order_approval_records:
            order_ids = order_approval_records.values_list("object_id", flat=True)
            Order.objects.filter(id__in=order_ids).update(created_approval_by_pi=True)
            order_approval_records.delete()
            msg["success_message"] = True
    else:
        messages.error(request, "You are not allowed to approve orders")

    if msg["success_message"]:
        messages.success(request, "The records have been approved")

    if msg["warning_message"]:
        messages.warning(
            request,
            "Some/all of the records you have selected were not approved "
            "because you are not listed as a project leader for them",
        )

    return HttpResponseRedirect(".")


@admin.action(description="Notify users of required edits")
def notify_user_edits_required(modeladmin, request, queryset):
    """Notify a user that a collection record must be edited"""

    queryset = queryset.filter(content_type__app_label="collection")

    if queryset.filter(message=""):
        messages.error(
            request,
            "Some of the records you have selected do not have a message. "
            "Please add a message to them, and try again",
        )
        return HttpResponseRedirect(".")
    else:
        user_ids = set(queryset.values_list("activity_user", flat=True))
        now = timezone.now()
        for user_id in user_ids:
            user = User.objects.get(id=user_id)
            objs = queryset.filter(activity_user__id=user_id)
            for obj in objs:
                obj.content_object.absolute_url = request.build_absolute_uri(
                    reverse(
                        f"admin:{obj.content_object._meta.app_label}_"
                        f"{obj.content_object._meta.model_name}_change",
                        args=[obj.content_object.id],
                    )
                )

            message_txt = ""
            for obj in objs:
                message_txt = (
                    message_txt
                    + "\t".join(
                        (
                            str(obj.content_type.name).capitalize(),
                            str(obj.content_object),
                            obj.message,
                        )
                    ).strip()
                    + "\n"
                )

            message_txt = render_to_string(
                "admin/approval/approval/approval_email_request_changes.txt",
                {
                    "recipient": user,
                    "sender": request.user,
                    "objs_str": message_txt,
                    "site_title": SITE_TITLE,
                },
            )

            message_html = render_to_string(
                "admin/approval/approval/approval_email_request_changes.html",
                {
                    "recipient": user,
                    "sender": request.user,
                    "objs": objs,
                    "site_title": SITE_TITLE,
                },
            )

            send_mail(
                "Some records that you have created or changed need your attention",
                message_txt,
                SERVER_EMAIL_ADDRESS,
                [user.email],
                html_message=message_html,
                fail_silently=False,
            )
        messages.success(request, "Users have been notified of required edits")
        queryset.update(message_date_time=now, edited=False)
        return HttpResponseRedirect(".")


@admin.action(description="Approve all new orders")
def approve_all_new_orders(modeladmin, request, queryset):
    """Approve all new orders"""

    if request.user.is_pi:
        orders = Order.objects.filter(created_approval_by_pi=False)
        if orders.exists():
            orders.update(created_approval_by_pi=True)
            Approval.objects.filter(content_type__app_label="ordering").delete()
            messages.success(request, "New orders have been approved")
        else:
            messages.warning(request, "No new orders to approve")
    else:
        messages.error(request, "You are not allowed to approve orders")

    return HttpResponseRedirect(".")
