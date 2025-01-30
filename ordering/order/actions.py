import datetime
import json

from adminactions.mass_update import (
    ActionInterrupted,
    adminaction_end,
    adminaction_requested,
    adminaction_start,
)
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.db.transaction import atomic
from django.forms.models import ModelMultipleChoiceField, modelform_factory
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.encoding import smart_str
from django.utils.safestring import mark_safe

from common.shared import export_objects

from .export import OrderChemicalExportResource, OrderExportResource
from .forms import MassUpdateOrderForm

SITE_TITLE = getattr(settings, "SITE_TITLE", "Lab DB")
SERVER_EMAIL_ADDRESS = getattr(settings, "SERVER_EMAIL_ADDRESS", "noreply@example.com")


def change_order_status(request, queryset, origin_status, destination_status):
    """
    Change the status of selected orders
    """

    # Only Lab or Order Manager can use this action
    if not (
        request.user.groups.filter(name="Lab manager").exists()
        or request.user.groups.filter(name="Order manager").exists()
    ):
        messages.error(request, "Nice try, you are not allowed to do that.")
        return
    else:
        for order in queryset.filter(status=origin_status):
            order.status = destination_status
            order.save()


@admin.action(description="Change STATUS to ARRANGED")
def change_order_status_to_arranged(modeladmin, request, queryset):
    """
    Action to change the status of selected orders from open to
    arranged
    """

    change_order_status(request, queryset, "open", "arranged")


@admin.action(description="Change STATUS to USED UP")
def change_order_status_to_used_up(modeladmin, request, queryset):
    """
    Action to change the status of selected orders from delivered to
    used up
    """

    change_order_status(request, queryset, "delivered", "used up")


@admin.action(description="Change STATUS to DELIVERED")
def change_order_status_to_delivered(modeladmin, request, queryset):
    """
    Action to change the status of selected orders from arranged to
    delivered
    """

    # Only Lab or Order Manager can use this action
    if not (
        request.user.groups.filter(name="Lab manager").exists()
        or request.user.groups.filter(name="Order manager").exists()
    ):
        messages.error(request, "Nice try, you are not allowed to do that.")
        return
    else:
        for order in queryset.filter(status="arranged"):
            # If an order does not have a delivery date and its status changes
            # to 'delivered', set the date for delivered_date to the current
            # date.
            order.status = "delivered"
            order.delivered_date = datetime.date.today()

            # If delivery notification wanted, send it and set sent_email to true
            # to remember that an email has been sent out
            if order.delivery_alert and not order.sent_email:
                order.sent_email = True
                message = render_to_string(
                    "admin/ordering/order/order_email_delivered.txt",
                    {"order": order, "SITE_TITLE": SITE_TITLE},
                )
                send_mail(
                    "Delivery notification",
                    message,
                    SERVER_EMAIL_ADDRESS,
                    [order.created_by.email],
                    fail_silently=True,
                )
            order.save()


@admin.action(description="Export orders")
def export_orders(modeladmin, request, queryset):
    """
    Action to export orders
    """

    export_data = OrderExportResource().export(queryset)
    return export_objects(request, queryset, export_data)


@admin.action(description="Export as chemical")
def export_chemicals(modeladmin, request, queryset):
    """
    Action to export an order as a chemical
    """

    export_data = OrderChemicalExportResource().export(queryset)
    response = export_objects(request, queryset, export_data)
    response["Content-Disposition"] = response["Content-Disposition"].replace(
        "Order_", "Chemical_"
    )
    return response


@admin.action(description="Mass update")
def mass_update(modeladmin, request, queryset):
    """
    Mass update queryset
    From adminactions.mass_update
    Modified to allow specifiying a custom form
    """

    def not_required(field, **kwargs):
        """force all fields as not required and return modeladmin field"""
        kwargs["required"] = False
        kwargs["request"] = request
        return modeladmin.formfield_for_dbfield(field, **kwargs)

    def _doit():
        errors = {}
        updated = 0
        for record in queryset:
            for field_name, value_or_func in list(form.cleaned_data.items()):
                if callable(value_or_func):
                    old_value = getattr(record, field_name)
                    setattr(record, field_name, value_or_func(old_value))
                else:
                    setattr(record, field_name, value_or_func)
            if clean:
                record.clean()
            record.save()
            updated += 1
        if updated:
            messages.info(request, f"Updated {updated} records")

        if len(errors):
            messages.error(request, "%s records not updated due errors" % len(errors))
        adminaction_end.send(
            sender=modeladmin.model,
            action="mass_update",
            request=request,
            queryset=queryset,
            modeladmin=modeladmin,
            form=form,
            errors=errors,
            updated=updated,
        )

    # Only Lab or Order Managers
    if not (
        request.user.groups.filter(name="Lab manager").exists()
        or request.user.groups.filter(name="Order manager").exists()
    ):
        messages.error(request, "Nice try, you are not allowed to do that.")
        return

    try:
        adminaction_requested.send(
            sender=modeladmin.model,
            action="mass_update",
            request=request,
            queryset=queryset,
            modeladmin=modeladmin,
        )
    except ActionInterrupted as e:
        messages.error(request, str(e))
        return

    # Allows to specify a custom mass update Form in the ModelAdmin

    mass_update_form = MassUpdateOrderForm
    mass_update_fields = getattr(modeladmin, "mass_update_fields", None)
    mass_update_exclude = getattr(modeladmin, "mass_update_exclude", ["pk"]) or []
    if "pk" not in mass_update_exclude:
        mass_update_exclude.append("pk")

    if mass_update_fields and mass_update_exclude:
        raise Exception(
            "Cannot set both 'mass_update_exclude' and 'mass_update_fields'"
        )
    MForm = modelform_factory(
        modeladmin.model,
        form=mass_update_form,
        exclude=mass_update_exclude,
        fields=mass_update_fields,
        formfield_callback=not_required,
    )
    selected_fields = []
    initial = {
        "_selected_action": request.POST.getlist(helpers.ACTION_CHECKBOX_NAME),
        "select_across": request.POST.get("select_across") == "1",
        "action": "mass_update",
    }

    if "apply" in request.POST:
        form = MForm(request.POST)
        if form.is_valid():
            try:
                adminaction_start.send(
                    sender=modeladmin.model,
                    action="mass_update",
                    request=request,
                    queryset=queryset,
                    modeladmin=modeladmin,
                    form=form,
                )
            except ActionInterrupted as e:
                messages.error(request, str(e))
                return HttpResponseRedirect(request.get_full_path())

            validate = form.cleaned_data.get("_validate", False)
            clean = form.cleaned_data.get("_clean", False)

            if validate:
                with atomic():
                    _doit()

            else:
                values = {}
                for field_name, value in list(form.cleaned_data.items()):
                    if isinstance(form.fields[field_name], ModelMultipleChoiceField):
                        # Handle M2M fields
                        if field_name in [
                            "ghs_symbols",
                            "signal_words",
                            "hazard_statements",
                        ]:
                            for e in queryset:
                                field = getattr(e, field_name)
                                field.clear()
                                field.add(*value)
                            history_ids = list(
                                value.order_by("id")
                                .distinct("id")
                                .values_list("id", flat=True)
                            )
                            queryset.update(**{f"history_{field_name}": history_ids})
                        else:
                            messages.error(
                                request,
                                "Unable to mass update ManyToManyField without 'validate'",
                            )
                            return HttpResponseRedirect(request.get_full_path())
                    elif callable(value):
                        messages.error(
                            request,
                            "Unable to mass update using operators without 'validate'",
                        )
                        return HttpResponseRedirect(request.get_full_path())
                    elif field_name not in [
                        "_selected_action",
                        "_validate",
                        "select_across",
                        "action",
                        "_unique_transaction",
                        "_clean",
                    ]:
                        values[field_name] = value
                messages.info(request, f"Updated {len(queryset)} records")
                queryset.update(**values)

            return HttpResponseRedirect(request.get_full_path())
    else:
        initial.update({"action": "mass_update", "_validate": 1})
        # form = MForm(initial=initial)
        prefill_with = request.POST.get("prefill-with", None)
        prefill_instance = None
        try:
            # Gets the instance directly from the queryset for data security
            prefill_instance = queryset.get(pk=prefill_with)
        except ObjectDoesNotExist:
            pass

        form = MForm(initial=initial, instance=prefill_instance)

    adminForm = helpers.AdminForm(
        form, modeladmin.get_fieldsets(request), {}, [], model_admin=modeladmin
    )
    media = modeladmin.media + adminForm.media
    dthandler = (
        lambda obj: obj.isoformat() if isinstance(obj, datetime.date) else str(obj)
    )
    tpl = "adminactions/mass_update.html"
    ctx = {
        "adminform": adminForm,
        "form": form,
        "action_short_description": mass_update.short_description,
        "title": "%s (%s)"
        % (
            mass_update.short_description.capitalize(),
            smart_str(modeladmin.opts.verbose_name_plural),
        ),
        "grouped": {},
        "fieldvalues": json.dumps({}, default=dthandler),
        "change": True,
        "selected_fields": selected_fields,
        "is_popup": False,
        "save_as": False,
        "has_delete_permission": False,
        "has_add_permission": False,
        "has_change_permission": True,
        "opts": modeladmin.model._meta,
        "app_label": modeladmin.model._meta.app_label,
        "media": mark_safe(media),
        "selection": queryset,
    }
    ctx.update(modeladmin.admin_site.each_context(request))

    return render(request, tpl, context=ctx)
