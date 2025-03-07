import json

import requests
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.db import models
from django.db.models import Subquery
from django.http import HttpResponse, HttpResponseRedirect
from django.template.loader import render_to_string
from django.urls import path, re_path, reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from djangoql.admin import DjangoQLSearchMixin

from common.admin import (
    AdminChangeFormWithNavigation,
    SimpleHistoryWithSummaryAdmin,
    save_history_fields,
)

from ..models import (
    CostUnit,
    Location,
    Order,
    OrderExtraDoc,
)
from .actions import (
    change_order_status_to_arranged,
    change_order_status_to_delivered,
    change_order_status_to_used_up,
    export_chemicals,
    export_orders,
    mass_update,
)
from .forms import MassUpdateOrderForm, OrderAdminForm
from .search import OrderQLSchema

ORDER_EMAIL_ADDRESSES = getattr(
    settings, "ORDER_EMAIL_ADDRESSES", ["noreply@example.com"]
)
MS_TEAMS_WEBHOOK = getattr(settings, "MS_TEAMS_WEBHOOK", "")
TIME_ZONE = settings.TIME_ZONE
SITE_TITLE = getattr(settings, "SITE_TITLE", "Lab DB")
ALLOWED_HOSTS = getattr(settings, "ALLOWED_HOSTS", [])
SERVER_EMAIL_ADDRESS = getattr(settings, "SERVER_EMAIL_ADDRESS", "noreply@example.com")


class OrderAdminSite(admin.AdminSite):
    def get_order_urls(self):
        urls = [
            path(
                "ordering/my_orders_redirect",
                self.admin_view(self.my_orders_redirect_view),
            ),
            re_path(
                r"^ordering/order_autocomplete/(?P<field>.*)=(?P<query>.*),(?P<timestamp>.*)",
                self.admin_view(self.autocomplete_order_view),
            ),
        ]

        return urls

    def my_orders_redirect_view(self, request):
        """
        View to redirect a user to its My Orders page
        """

        return HttpResponseRedirect(
            f'/ordering/order/?q-l=on&q=created_by.username+%3D+"{request.user.username}"'
        )

    def autocomplete_order_view(self, request, *args, **kwargs):
        """
        View for order autocompletion values.
        Given an order's product name or catalogue number, returns
        a json list of possible hits to be used for autocompletion
        """

        # Get field name and search query from url
        query_field_name = kwargs.get("field")
        search_query = kwargs.get("query")

        if not (
            query_field_name in ["part_description", "supplier_part_no"]
            and search_query
        ):
            return HttpResponse(
                json.dumps([], ensure_ascii=False),
                content_type="application/json",
            )

        first_export_field = (
            "supplier_part_no"
            if query_field_name == "part_description"
            else "part_description"
        )
        export_fields = [
            first_export_field,
            "supplier",
            "location_id",
            "msds_form_id",
            "price",
            "cas_number",
            "history_ghs_symbols",
            "history_signal_words",
            "history_hazard_statements",
            "hazard_level_pregnancy",
        ]

        # Get the last 10 unique orders that match query_field_name
        # and search_query
        orders = (
            Order.objects.filter(
                pk__in=Subquery(
                    Order.objects.filter(
                        **{f"{query_field_name}__icontains": search_query}
                    )
                    .exclude(supplier_part_no__icontains="?")
                    .exclude(supplier_part_no="")
                    .exclude(part_description__iexact="none")
                    .distinct("part_description")
                    .order_by("part_description", "-pk")
                    .values("pk")
                )
            )
            .order_by("-pk")
            .only(*export_fields)[:10]
        )

        # Serialize orders
        orders_for_autocomplete = [
            {
                "label": getattr(order, query_field_name),
                "data": {
                    field.replace("_id", "").replace("history_", ""): getattr(
                        order, field
                    )
                    for field in export_fields
                },
            }
            for order in orders
        ]
        return HttpResponse(
            json.dumps(orders_for_autocomplete, ensure_ascii=False),
            content_type="application/json",
        )


class OrderExtraDocInline(admin.TabularInline):
    """
    Inline to view existing extra order documents
    """

    model = OrderExtraDoc
    verbose_name_plural = "Existing extra docs"
    extra = 0
    fields = ["get_doc_short_name", "description"]
    readonly_fields = ["get_doc_short_name", "description"]

    def has_add_permission(self, request, obj):
        # Prevent users from adding new objects for this inline
        return False

    @admin.display(description="Document")
    def get_doc_short_name(self, instance):
        """
        Returns the url of an order document as a HTML <a> tag with
        text View
        """

        if instance.name:
            return mark_safe(f'<a href="{instance.name.url}">View</a>')
        else:
            return ""


class AddOrderExtraDocInline(admin.TabularInline):
    """
    Inline to add new extra order documents
    """

    model = OrderExtraDoc
    verbose_name_plural = "New extra docs"
    extra = 0
    fields = ["name", "description"]

    def has_change_permission(self, request, obj=None):
        # Prevent users from changing existing objects for this inline
        return False

    def get_readonly_fields(self, request, obj=None):
        # If User is not a Lab or Order Manager set the name and description
        # attributes as read-only
        if obj:
            if not (
                request.user.is_superuser
                or request.user.groups.filter(
                    name__in=["Lab manager", "Order manager"]
                ).exists()
            ):
                return ["name", "description"]
            else:
                return []
        else:
            return []

    def get_queryset(self, request):
        return OrderExtraDoc.objects.none()


class OrderAdmin(
    DjangoQLSearchMixin, SimpleHistoryWithSummaryAdmin, AdminChangeFormWithNavigation
):
    list_display = (
        "custom_internal_order_no",
        "item_description",
        "supplier_and_part_no",
        "quantity",
        "price",
        "cost_unit_name",
        "trimmed_comment",
        "location",
        "msds_link",
        "coloured_status",
        "created_by",
    )
    list_display_links = ("custom_internal_order_no",)
    list_per_page = 25
    inlines = [OrderExtraDocInline, AddOrderExtraDocInline]
    djangoql_schema = OrderQLSchema
    djangoql_completion_enabled_by_default = False
    mass_update_form = MassUpdateOrderForm
    actions = [
        change_order_status_to_arranged,
        change_order_status_to_delivered,
        change_order_status_to_used_up,
        export_orders,
        export_chemicals,
        mass_update,
    ]
    search_fields = ["id", "part_description", "supplier_part_no"]
    form = OrderAdminForm
    raw_id_fields = ["ghs_symbols", "msds_form", "signal_words", "hazard_statements"]
    autocomplete_fields = []
    m2m_save_ignore_fields = []
    obj_specific_fields = [
        "internal_order_no",
        "supplier",
        "supplier_part_no",
        "part_description",
        "quantity",
        "price",
        "cost_unit",
        "status",
        "urgent",
        "delivery_alert",
        "location",
        "comment",
        "url",
    ]
    safety_info_fields = [
        "cas_number",
        "ghs_symbols",
        "ghs_pict_img",
        "signal_words",
        "msds_form",
        "hazard_statements",
        "hazard_level_pregnancy",
    ]

    obj_unmodifiable_fields = [
        "created_date_time",
        "last_changed_date_time",
        "order_manager_created_date_time",
        "delivered_date",
        "created_by",
    ]

    @admin.display(description="Part description", ordering="part_description")
    def item_description(self, instance):
        """
        More nicely formatted description field
        """

        part_description = instance.part_description.strip()
        part_description = part_description
        if instance.status != "cancelled":
            return part_description
        else:
            return mark_safe(
                f'<span style="text-decoration: line-through;">{part_description}</span>'
            )

    @admin.display(description="Supplier - Part no.")
    def supplier_and_part_no(self, instance):
        """
        Custom supplier and part number field
        """

        supplier = (
            instance.supplier.strip() if instance.supplier.lower() != "none" else ""
        )
        for string in ["GmbH", "Chemie"]:
            supplier = supplier.replace(string, "").strip()
        supplier_part_no = (
            instance.supplier_part_no.strip()
            if instance.supplier_part_no != "none"
            else ""
        )
        if instance.status != "cancelled":
            if supplier_part_no:
                return f"{supplier} - {supplier_part_no}"
            else:
                return supplier
        else:
            if supplier_part_no:
                return mark_safe(
                    f'<span style="text-decoration: line-through;">{supplier} - {supplier_part_no}</span>'
                )
            else:
                return mark_safe(
                    f'<span style="text-decoration: line-through;">{supplier}</span>'
                )

    @admin.display(description="Status", ordering="status")
    def coloured_status(self, instance):
        """
        Custom coloured status field
        """

        if instance.status:
            status = (
                "urgent"
                if instance.urgent and instance.status == "submitted"
                else instance.status
            )
            message_status = (
                instance.delivered_date.strftime("%d.%m.%Y")
                if instance.delivered_date and status != "used up"
                else status.capitalize()
            )
            return mark_safe(
                f"<span class='order-status order-status-{status.replace(' ', '-')}'>{message_status}</span>"
            )
        else:
            return "-"

    @admin.display(description="Comments")
    def trimmed_comment(self, instance):
        """
        Custom comment field
        """

        comment = instance.comment
        if comment:
            return (
                mark_safe(f'<span title="{comment}">{comment[:65].strip()}...</span>')
                if len(comment) > 65
                else comment
            )
        else:
            None

    @admin.display(description="MSDS")
    def msds_link(self, instance):
        """
        Link to MSDS form
        """

        if instance.msds_form:
            return mark_safe(
                f'<a class="magnific-popup-iframe-msds" href="{instance.msds_form.name.url}">View</a>'
            )
        else:
            None

    @admin.display(description="ID", ordering="id")
    def custom_internal_order_no(self, instance):
        """
        Custom internal order no field
        """

        if str(instance.internal_order_no).startswith(str(instance.id)):
            return instance.internal_order_no
        else:
            return str(instance.id)

    @admin.display(description="Cost unit", ordering="cost_unit__name")
    def cost_unit_name(self, instance):
        return instance.cost_unit.name

    def save_model(self, request, obj, form, change):
        # Save new order
        def save_new(request, obj):
            # If an order is new, assign the request user to it only if the
            # order's created_by attribute is not null
            obj.id = (
                self.model.objects.order_by("-id").first().id + 1
                if self.model.objects.exists()
                else 1
            )
            try:
                obj.created_by
            except Exception:
                obj.created_by = request.user
            obj.save()
            # Automatically create internal_order_number and add it
            # to record
            if not obj.internal_order_no:
                obj.internal_order_no = (
                    f"{obj.pk}-{timezone.now().date().strftime('%y%m%d')}"
                )
            obj.save()
            # Delete the first history record, which doesn't contain an
            # internal_order_number, and change the newer history record's
            # history_type from changed (~) to created (+). This gets rid of a
            # duplicate history record created when automatically generating
            # an internal_order_number
            obj.history.last().delete()
            history_obj = obj.history.first()
            history_obj.history_type = "+"
            history_obj.save()
            # Create approval record
            if not request.user.labuser.is_principal_investigator:
                obj.approval.create(
                    activity_type="created",
                    activity_user=obj.history.latest().created_by,
                )
                self.model.objects.filter(id=obj.pk).update(created_approval_by_pi=True)
            # Send email to Lab Managers if an order is urgent
            if obj.urgent:
                post_message_status_code = 0
                current_site = ALLOWED_HOSTS[0]
                order_change_url = (
                    f"{request.scheme + '://' if request.scheme else ''}{current_site}"
                    f"{reverse('admin:ordering_order_change', args=(obj.id,))}"
                )
                # If MS Teams webhook exists, send urgent order notification to it,
                if MS_TEAMS_WEBHOOK:
                    try:
                        message_card = render_to_string(
                            "admin/ordering/order/order_msteams_card_urgent.json",
                            {
                                "order": obj,
                                "created_by": request.user,
                                "created_date_time": timezone.localtime(
                                    obj.created_date_time
                                ).strftime("%d.%m.%Y %H:%m"),
                                "order_change_url": order_change_url,
                            },
                        )
                        message_card = json.loads(message_card)
                        post_message = requests.post(
                            url=MS_TEAMS_WEBHOOK, json=message_card
                        )
                        post_message_status_code = post_message.status_code

                    except Exception:
                        pass
                # if not, send email
                if post_message_status_code != 200:
                    message = render_to_string(
                        "admin/ordering/order/order_email_urgent.txt",
                        {"user": request.user, "order": obj, "site_title": SITE_TITLE},
                    )
                    try:
                        send_mail(
                            "New urgent order",
                            message,
                            SERVER_EMAIL_ADDRESS,
                            ORDER_EMAIL_ADDRESSES,
                            fail_silently=False,
                        )
                        messages.success(
                            request,
                            "The lab managers have been informed of your urgent order.",
                        )
                    except Exception:
                        messages.warning(
                            request,
                            "Your urgent order was added to the Order list. However, the lab managers have not been informed of it.",
                        )

        # Save existing order
        def save_existing(request, obj):
            # Allow only Lab and Order managers to change an order
            if not (
                request.user.groups.filter(
                    name__in=["Lab manager", "Order manager"]
                ).exists()
            ):
                raise PermissionDenied

            else:
                order = self.model.objects.get(pk=obj.pk)

                # If the status of an order changes to the following
                if obj.status != order.status:
                    if not order.order_manager_created_date_time:
                        # If an order's status changed from 'submitted' to any other,
                        # set the date-time for order_manager_created_date_time to the
                        # current date-time
                        if obj.status in ["open", "arranged", "delivered"]:
                            obj.order_manager_created_date_time = timezone.now()

                    # If an order does not have a delivery date and its status changes
                    # to 'delivered', set the date for delivered_date to the current
                    # date. If somebody requested a delivery notification, send it and
                    # set sent_email to true to remember that an email has already been
                    # sent out
                    if not order.delivered_date and obj.status == "delivered":
                        obj.delivered_date = timezone.now().date()
                        if order.delivery_alert and not order.sent_email:
                            obj.sent_email = True
                            message = render_to_string(
                                "admin/ordering/order/order_email_delivered.txt",
                                {"order": order, "site_title": SITE_TITLE},
                            )
                            try:
                                send_mail(
                                    "Delivery notification",
                                    message,
                                    SERVER_EMAIL_ADDRESS,
                                    [obj.created_by.email],
                                    fail_silently=False,
                                )
                                messages.success(
                                    request, "Delivery notification was sent."
                                )
                            except Exception:
                                messages.warning(
                                    request,
                                    "Could not send delivery notification.",
                                )
            obj.save()
            # Delete order history for used-up or cancelled items
            if obj.status in ["used up", "cancelled"] and obj.history.exists():
                obj_history = obj.history.all()
                obj_history.delete()

        if obj.pk is None:
            # Save new order
            save_new(request, obj)
        else:
            # Save existing order
            save_existing(request, obj)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        obj = self.model.objects.get(pk=form.instance.id)
        try:
            history_obj = obj.history.latest()
        except Exception:
            history_obj = None
        save_history_fields(self, obj, history_obj)

    def get_queryset(self, request):
        # Allows sorting of custom changelist_view fields by adding
        # admin_order_field property to said custom field, also excludes
        # cancelled orders, to make things prettier"""
        qs = super().get_queryset(request)
        qs = qs.annotate(
            models.Count("id"), models.Count("part_description"), models.Count("status")
        )
        if not (
            request.user.groups.filter(
                name__in=["Lab manager", "Order manager"]
            ).exists()
            or request.user.is_superuser
        ):
            return qs.exclude(status="cancelled")
        else:
            return qs

    def get_readonly_fields(self, request, obj=None):
        if obj:
            if self.can_change:
                return self.obj_specific_fields[8:10] + self.obj_unmodifiable_fields
            else:
                return (
                    self.obj_specific_fields
                    + self.safety_info_fields
                    + self.obj_unmodifiable_fields
                )
        else:
            return self.obj_unmodifiable_fields[:3]

    def add_view(self, request, extra_context=None):
        self.raw_id_fields = self.safety_info_fields[1:-1]
        self.autocomplete_fields = []
        if (
            request.user.groups.filter(
                name__in=["Lab manager", "Order manager"]
            ).exists()
            or request.user.is_superuser
        ):
            safety_info_fields = self.safety_info_fields.copy()
            safety_info_fields.remove("ghs_pict_img")
            self.fieldsets = (
                (
                    None,
                    {"fields": self.obj_specific_fields + ["created_by"]},
                ),
                (
                    "SAFETY INFORMATION",
                    {"classes": ("collapse",), "fields": safety_info_fields},
                ),
            )
        else:
            self.fieldsets = (
                (
                    None,
                    {"fields": self.obj_specific_fields[1:]},
                ),
                (
                    "SAFETY INFORMATION",
                    {"classes": ("collapse",), "fields": safety_info_fields},
                ),
            )
        return super().add_view(request, extra_context=extra_context)

    def change_view(self, request, object_id, extra_context=None):
        self.can_change = False
        if object_id:
            self.autocomplete_fields = self.safety_info_fields[1:-1]
            self.raw_id_fields = []
            extra_context = extra_context or {}
            self.fieldsets = (
                (
                    None,
                    {"fields": self.obj_specific_fields + self.obj_unmodifiable_fields},
                ),
                (
                    "SAFETY INFORMATION",
                    {"fields": self.safety_info_fields},
                ),
            )

            if (
                request.user.groups.filter(
                    name__in=["Lab manager", "Order manager"]
                ).exists()
                or request.user.is_superuser
            ):
                self.can_change = True
                extra_context = {
                    "show_close": True,
                    "show_save_and_add_another": True,
                    "show_save_and_continue": True,
                    "show_save_as_new": False,
                    "show_save": True,
                }

            else:
                extra_context = {
                    "show_close": True,
                    "show_save_and_add_another": False,
                    "show_save_and_continue": False,
                    "show_save_as_new": False,
                    "show_save": False,
                }

        else:
            self.autocomplete_fields = []
            self.raw_id_fields = self.safety_info_fields[1:-1]

        return super().change_view(request, object_id, extra_context=extra_context)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        # Set the value of the custom ghs_pict_img field when an order exists
        # otherwise remove field
        if obj:
            form.base_fields["ghs_pict_img"].initial = str(
                list(
                    obj.ghs_symbols.filter(pictogram__isnull=False).values_list(
                        "id", flat=True
                    )
                )
                if obj.ghs_symbols.all().exists()
                else []
            )
        else:
            form.base_fields.pop("ghs_pict_img")
        return form

    def get_formsets_with_inlines(self, request, obj=None):
        # Remove AddOrderExtraDocInline from add/change form if user who
        # created an Order object is not the request user a Lab manager
        # or a superuser
        if obj:
            for inline in self.get_inline_instances(request, obj):
                if inline.verbose_name_plural == "Existing extra docs":
                    yield inline.get_formset(request, obj), inline
                else:
                    if (
                        request.user.is_superuser
                        or request.user.groups.filter(
                            name__in=["Lab manager", "Order manager"]
                        ).exists()
                    ):
                        yield inline.get_formset(request, obj), inline
        else:
            for inline in self.get_inline_instances(request, obj):
                if inline.verbose_name_plural == "Existing extra docs":
                    continue
                else:
                    yield inline.get_formset(request, obj), inline

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        try:
            request.resolver_match.args[0]
        except Exception:
            # Exclude certain users from the 'Created by' field in the order form
            if db_field.name == "created_by":
                if (
                    request.user.is_superuser
                    or request.user.groups.filter(
                        name__in=["Lab manager", "Order manager"]
                    ).exists()
                ):
                    kwargs["queryset"] = User.objects.exclude(
                        username__in=["admin", "guest", "AnonymousUser"]
                    ).order_by("last_name")
                kwargs["initial"] = request.user.id

            # Sort cost_unit and locations fields by name
            if db_field.name == "cost_unit":
                kwargs["queryset"] = CostUnit.objects.exclude(status=True).order_by(
                    "name"
                )
            if db_field.name == "location":
                kwargs["queryset"] = Location.objects.exclude(status=True).order_by(
                    "name"
                )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


#################################################
#            ORDER EXTRA DOC PAGES              #
#################################################


class OrderExtraDocAdmin(DjangoQLSearchMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "name",
    )
    list_display_links = (
        "id",
        "name",
    )
    list_per_page = 25
    ordering = ["id"]

    def has_module_permission(self, request):
        # Hide module from Admin
        return False

    def get_readonly_fields(self, request, obj=None):
        # Specifies which fields should be shown as read-only and when

        if obj:
            return [
                "name",
                "order",
                "created_date_time",
            ]

    def add_view(self, request, extra_context=None):
        # Specifies which fields should be shown in the add view
        self.fields = [
            "name",
            "order",
            "created_date_time",
        ]
        return super().add_view(request)

    def change_view(self, request, object_id, extra_context=None):
        # Specifies which fields should be shown in the change view
        self.fields = [
            "name",
            "order",
            "created_date_time",
        ]
        return super().change_view(request, object_id)
