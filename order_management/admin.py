#################################################
#    DJANGO 'CORE' FUNCTIONALITIES IMPORTS      #
#################################################

from django.contrib import admin
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import models
from django.http import HttpResponse
from django.db.models.functions import Length
from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext as _
from django import forms
from django.conf.urls import url
from django.contrib.admin.widgets import AdminFileWidget

#################################################
#          DJANGO PROJECT SETTINGS              #
#################################################

from django_project.private_settings import SITE_TITLE
from django_project.private_settings import SERVER_EMAIL_ADDRESS
from my_admin.models import GeneralSetting

from django_project.settings import TIME_ZONE
from django_project.private_settings import ALLOWED_HOSTS

#################################################
#        ADDED FUNCTIONALITIES IMPORTS          #
#################################################

# Advanced search functionalities from DjangoQL
from djangoql.admin import DjangoQLSearchMixin
from djangoql.schema import DjangoQLSchema, StrField
from collection_management.admin import SearchFieldOptUsername, SearchFieldOptLastname

# Object history tracking from django-simple-history
from collection_management.admin import SimpleHistoryWithSummaryAdmin

# Import/Export functionalities from django-import-export
from import_export.admin import ExportActionModelAdmin
from import_export.fields import Field

# Background tasks
from background_task import background

# Mass update
from adminactions.mass_update import MassUpdateForm, get_permission_codename,\
    ActionInterrupted, adminaction_requested, adminaction_start, adminaction_end

from jsmin import jsmin
import xlrd
import csv
import requests
import pytz
import datetime
import time
import inspect
from ast import literal_eval

#################################################
#                OTHER IMPORTS                  #
#################################################

from .models import OrderExtraDoc
from .models import Order
from .models import Location
from .models import CostUnit
from .models import MsdsForm
from .models import GhsSymbol
from .models import SignalWord

#################################################
#                ORDER ADMIN                    #
#################################################

class OrderAdmin(admin.AdminSite):
    
    def get_order_urls(self):

        urls = [url(r'^order_management/my_orders_redirect$', self.admin_view(self.my_orders_redirect_view)),
                url(r'^order_management/order_autocomplete/(?P<field>.*)=(?P<query>.*),(?P<timestamp>.*)', self.admin_view(self.autocomplete_order_view))]

        return urls
    
    def my_orders_redirect_view(self, request):
        """ Redirect a user to its My Orders page """

        from django.http import HttpResponseRedirect

        return HttpResponseRedirect('/order_management/order/?q-l=on&q=created_by.username+%3D+"{}"'.format(request.user.username))

    def autocomplete_order_view(self, request, *args, **kwargs):
        """Given an order's product name or number, returns a json list of possible
        hits to be used for autocompletion"""

        # Get field and query from url
        field = kwargs['field']
        query = kwargs['query']

        # Get possible hits
        orders = Order.objects.filter(**{'{}__icontains'.format(field): query}) \
                                .exclude(supplier_part_no__icontains="?") \
                                .exclude(supplier_part_no="") \
                                .exclude(part_description__iexact="none") \
                                .order_by('-id')[:50] \
                                .values("supplier", "supplier_part_no", "part_description", "location", "msds_form", "price", "cas_number", "hazard_level_pregnancy", "ghs_symbols_autocomplete", "signal_words_autocomplete")

        # Generate json
        lstofprodname = []
        json_line = ""

        if field == "part_description":
        
            # Loop through all elements (= rows) in the order list
            for order in orders:
                
                # Create value:data pairs using part_description or supplier_part_no as values
                part_description_lower = order["part_description"].lower()
                
                if part_description_lower not in lstofprodname:

                    if len(lstofprodname) > 10: break
                        
                    json_line = json_line + '{{"value":"{}","data":"{}§§{}§§{}§§{}§§{}§§{}§§{}§§{}§§{}"}},'.format(
                        order["part_description"], 
                        order["supplier_part_no"], 
                        order["supplier"], 
                        order["location"],
                        order["msds_form"] if order["msds_form"] else 0,
                        order["price"],
                        order["cas_number"], 
                        order["ghs_symbols_autocomplete"],
                        order["signal_words_autocomplete"],
                        order["hazard_level_pregnancy"])
                    
                    lstofprodname.append(part_description_lower)

        elif field == "supplier_part_no":
                        
            # Loop through all elements (= rows) in the order list
            for order in orders:
                
                # Create value:data pairs using part_description or supplier_part_no as values
                part_description_lower = order["part_description"].lower()
                
                if part_description_lower not in lstofprodname:

                    if len(lstofprodname) > 10: break
                        
                    json_line = json_line + '{{"value":"{}","data":"{}§§{}§§{}§§{}§§{}§§{}§§{}§§{}§§{}"}},'.format(
                        order["supplier_part_no"], 
                        order["part_description"], 
                        order["supplier"], 
                        order["location"],
                        order["msds_form"] if order["msds_form"] else 0,
                        order["price"],
                        order["cas_number"], 
                        order["ghs_symbols_autocomplete"],
                        order["signal_words_autocomplete"],
                        order["hazard_level_pregnancy"])
                    
                    lstofprodname.append(part_description_lower)

        json_out = """[{}]""".format(json_line[:-1])

        return HttpResponse(json_out, content_type='application/json')

#################################################
#         CUSTOM MASS UPDATE FUNCTION           #
#################################################

def mass_update(modeladmin, request, queryset):
    """
        mass update queryset
        From adminactions.mass_update. Modified to allow specifiying a custom form
    """

    import json
    from collections import defaultdict

    from django.contrib.admin import helpers
    from django.core.exceptions import ObjectDoesNotExist
    from django.db.models import ForeignKey, fields as df
    from django.db.transaction import atomic
    from django.forms.models import (InlineForeignKeyField,
                                    ModelMultipleChoiceField, construct_instance,
                                    modelform_factory, )
    from django.http import HttpResponseRedirect
    from django.shortcuts import render
    from django.utils.encoding import smart_str

    def not_required(field, **kwargs):
        """force all fields as not required and return modeladmin field"""
        kwargs['required'] = False
        kwargs['request'] = request
        return modeladmin.formfield_for_dbfield(field, **kwargs)

    def _get_sample():
        for f in mass_update_hints:
            if isinstance(f, ForeignKey):
                # Filter by queryset so we only get results without our
                # current resultset
                filters = {"%s__in" % f.remote_field.name: queryset}
                # Order by random to get a nice sample
                query = f.related_model.objects.filter(**filters).distinct().order_by('?')
                # Limit the amount of results so we don't accidently query
                # many thousands of items and kill the database.
                grouped[f.name] = [(a.pk, str(a)) for a in query[:10]]
            elif hasattr(f, 'flatchoices') and f.flatchoices:
                grouped[f.name] = dict(getattr(f, 'flatchoices')).keys()
            elif hasattr(f, 'choices') and f.choices:
                grouped[f.name] = dict(getattr(f, 'choices')).keys()
            elif isinstance(f, df.BooleanField):
                grouped[f.name] = [("True", True), ("False", False)]

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
            messages.info(request, _("Updated %s records") % updated)

        if len(errors):
            messages.error(request, "%s records not updated due errors" % len(errors))
        adminaction_end.send(sender=modeladmin.model,
                             action='mass_update',
                             request=request,
                             queryset=queryset,
                             modeladmin=modeladmin,
                             form=form,
                             errors=errors,
                             updated=updated)

    opts = modeladmin.model._meta
    perm = "{0}.{1}".format(opts.app_label, get_permission_codename('adminactions_massupdate', opts))
    if not (request.user.groups.filter(name='Lab manager').exists() or request.user.groups.filter(name='Order manager').exists()):
        messages.error(request, _('Nice try, you are not allowed to do that.'))
        return

    try:
        adminaction_requested.send(sender=modeladmin.model,
                                   action='mass_update',
                                   request=request,
                                   queryset=queryset,
                                   modeladmin=modeladmin)
    except ActionInterrupted as e:
        messages.error(request, str(e))
        return

    # Allows to specified a custom mass update Form in the ModelAdmin

    mass_update_form = getattr(modeladmin, 'mass_update_form', MassUpdateForm)
    mass_update_fields = getattr(modeladmin, 'mass_update_fields', None)
    mass_update_exclude = getattr(modeladmin, 'mass_update_exclude', ['pk']) or []
    if 'pk' not in mass_update_exclude:
        mass_update_exclude.append('pk')
    mass_update_hints = getattr(modeladmin, 'mass_update_hints',
                                [f.name for f in modeladmin.model._meta.fields])

    if mass_update_fields and mass_update_exclude:
        raise Exception("Cannot set both 'mass_update_exclude' and 'mass_update_fields'")
    MForm = modelform_factory(modeladmin.model, form=mass_update_form,
                              exclude=mass_update_exclude,
                              fields=mass_update_fields,
                              formfield_callback=not_required)
    grouped = defaultdict(lambda: [])
    selected_fields = []
    initial = {'_selected_action': request.POST.getlist(helpers.ACTION_CHECKBOX_NAME),
               'select_across': request.POST.get('select_across') == '1',
               'action': 'mass_update'}

    if 'apply' in request.POST:
        form = MForm(request.POST)
        if form.is_valid():
            try:
                adminaction_start.send(sender=modeladmin.model,
                                       action='mass_update',
                                       request=request,
                                       queryset=queryset,
                                       modeladmin=modeladmin,
                                       form=form)
            except ActionInterrupted as e:
                messages.error(request, str(e))
                return HttpResponseRedirect(request.get_full_path())

            # need_transaction = form.cleaned_data.get('_unique_transaction', False)
            validate = form.cleaned_data.get('_validate', False)
            clean = form.cleaned_data.get('_clean', False)

            if validate:
                with atomic():
                    _doit()

            else:
                success_message = False
                values = {}
                for field_name, value in list(form.cleaned_data.items()):
                    if isinstance(form.fields[field_name], ModelMultipleChoiceField):
                        if field_name == 'ghs_symbols' or field_name == 'signal_words':
                            if field_name == 'ghs_symbols':
                                for e in queryset:
                                    e.ghs_symbols.clear()
                                    e.ghs_symbols.add(*value)
                                history_ghs_symbols = str(tuple(value.order_by('code').values_list('code', flat=True))).replace(',)', ')')
                                ghs_symbols_autocomplete = str(tuple(value.order_by('id').values_list('id', flat=True))).replace(',)', ')').replace(" ", "")[1:-1]
                                queryset.update(history_ghs_symbols=history_ghs_symbols, ghs_symbols_autocomplete=ghs_symbols_autocomplete)
                            else:
                                for e in queryset:
                                    e.signal_words.clear()
                                    e.signal_words.add(*value)
                                history_signal_words = str(tuple(value.order_by('signal_word').values_list('signal_word', flat=True))).replace(',)', ')')
                                signal_words_autocomplete = str(tuple(value.order_by('id').values_list('id', flat=True))).replace(',)', ')').replace(" ", "")[1:-1]
                                queryset.update(history_signal_words=history_signal_words, signal_words_autocomplete=signal_words_autocomplete)

                            success_message = True
                        else:
                            messages.error(request, "Unable to mass update ManyToManyField without 'validate'")
                            return HttpResponseRedirect(request.get_full_path())
                    elif callable(value):
                        messages.error(request, "Unable to mass update using operators without 'validate'")
                        return HttpResponseRedirect(request.get_full_path())
                    elif field_name not in ['_selected_action', '_validate', 'select_across', 'action',
                                            '_unique_transaction', '_clean']:
                        values[field_name] = value
                messages.info(request, _("Updated %s records") % len(queryset))
                queryset.update(**values)

            return HttpResponseRedirect(request.get_full_path())
    else:
        initial.update({'action': 'mass_update', '_validate': 1})
        # form = MForm(initial=initial)
        prefill_with = request.POST.get('prefill-with', None)
        prefill_instance = None
        try:
            # Gets the instance directly from the queryset for data security
            prefill_instance = queryset.get(pk=prefill_with)
        except ObjectDoesNotExist:
            pass

        form = MForm(initial=initial, instance=prefill_instance)

    if mass_update_hints:
        _get_sample()
    already_grouped = set(grouped)
    for el in queryset.all()[:10]:
        for f in modeladmin.model._meta.fields:
            if f.name in mass_update_hints and f.name not in already_grouped:
                if isinstance(f, ForeignKey):
                    filters = {"%s__isnull" % f.remote_field.name: False}
                    grouped[f.name] = [(a.pk, str(a)) for a in
                                       f.related_model.objects.filter(**filters).distinct()]
                elif hasattr(f, 'flatchoices') and f.flatchoices:
                    grouped[f.name] = dict(getattr(f, 'flatchoices')).keys()
                elif hasattr(f, 'choices') and f.choices:
                    grouped[f.name] = dict(getattr(f, 'choices')).keys()
                elif isinstance(f, df.BooleanField):
                    grouped[f.name] = [("True", True), ("False", False)]
                else:
                    value = getattr(el, f.name)
                    target = [str(value), value]
                    if value is not None and target not in grouped[f.name] and len(grouped) <= 10:
                        grouped[f.name].append(target)

                    initial[f.name] = initial.get(f.name, value)
    adminForm = helpers.AdminForm(form, modeladmin.get_fieldsets(request), {}, [], model_admin=modeladmin)
    media = modeladmin.media + adminForm.media
    dthandler = lambda obj: obj.isoformat() if isinstance(obj, datetime.date) else str(obj)
    tpl = 'adminactions/mass_update.html'
    ctx = {'adminform': adminForm,
           'form': form,
           'action_short_description': mass_update.short_description,
           'title': u"%s (%s)" % (
               mass_update.short_description.capitalize(),
               smart_str(modeladmin.opts.verbose_name_plural),
           ),
           'grouped': grouped,
           'fieldvalues': json.dumps(grouped, default=dthandler),
           'change': True,
           'selected_fields': selected_fields,
           'is_popup': False,
           'save_as': False,
           'has_delete_permission': False,
           'has_add_permission': False,
           'has_change_permission': True,
           'opts': modeladmin.model._meta,
           'app_label': modeladmin.model._meta.app_label,
           # 'action': 'mass_update',
           # 'select_across': request.POST.get('select_across')=='1',
           'media': mark_safe(media),
           'selection': queryset}
    ctx.update(modeladmin.admin_site.each_context(request))

    return render(request, tpl, context=ctx)

mass_update.short_description = _("Mass update selected orders")

#################################################
#                 ORDER INLINES                 #
#################################################

class OrderExtraDocInline(admin.TabularInline):
    """Inline to view existing extra order documents"""

    model = OrderExtraDoc
    verbose_name_plural = "Existing extra docs"
    extra = 0
    fields = ['get_doc_short_name', 'description']
    readonly_fields = ['get_doc_short_name', 'description']

    def has_add_permission(self, request, obj):
        
        # Prevent users from adding new objects with this inline
        return False
    
    def get_doc_short_name(self, instance):
        '''Returns the url of an order document as a HTML <a> tag with 
        text View'''
        if instance.name:
            return mark_safe('<a href="{}">View</a>'.format(instance.name.url))
        else:
            return ''
    get_doc_short_name.short_description = 'Document'

class AddOrderExtraDocInline(admin.TabularInline):
    """Inline to add new extra order documents"""

    model = OrderExtraDoc
    verbose_name_plural = "New extra docs"
    extra = 0
    fields = ['name','description']

    def has_change_permission(self, request, obj=None):
        
        # Prevent users from changing existing objects with this inline
        return False

    def get_readonly_fields(self, request, obj=None):
        '''Defines which fields should be shown as read-only under which conditions'''

        # If user is not a Lab or Order Manager set the name and description attributes as read-only
        if obj:
            if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user.groups.filter(name='Order manager').exists()):
                return ['name','description']
            else:
                return []
        else:
            return []

    def get_queryset(self, request):
        return OrderExtraDoc.objects.none()

#################################################
#         ORDER IMPORT/EXPORT RESOURCE          #
#################################################

from import_export import resources

class BaseOrderResource(resources.ModelResource):
    """Defines custom fields"""

    ghs_symbols_field = Field(column_name='ghs_symbols')
    signal_words_field = Field(column_name='signal_words')

    def dehydrate_ghs_symbols_field(self, order):
        return str(tuple(order.ghs_symbols.all().values_list('code', flat=True))).replace("'", "").replace('"', "").replace(',)', ')')[1:-1]

    def dehydrate_signal_words_field(self, order):
        return str(tuple(order.signal_words.all().values_list('signal_word', flat=True))).replace("'", "").replace('"', "").replace(',)', ')')[1:-1]

class OrderChemicalExportResource(BaseOrderResource):
    """Defines a custom export resource class for chemicals"""
    
    class Meta:
        model = Order
        fields = ('id','supplier', 'supplier_part_no', 'part_description', 'quantity', 
        "location__name", "cas_number", 'ghs_symbols_field', 'signal_words_field', 
         'hazard_level_pregnancy')
        export_order = fields

class OrderExportResource(BaseOrderResource):
    """Defines a custom export resource class for orders"""

    class Meta:
        model = Order
        fields = ('id', 'internal_order_no', 'supplier', 'supplier_part_no', 'part_description', 'quantity', 
            'price', 'cost_unit__name', 'status', 'location__name', 'comment', 'url', 'delivered_date', 'cas_number', 
            'ghs_symbols_field', 'signal_words_field', 'hazard_level_pregnancy', 'created_date_time', 
            'order_manager_created_date_time', 'last_changed_date_time', 'created_by__username',)
        export_order = fields

#################################################
#                   ACTIONS                     #
#################################################

def change_order_status_to_arranged(modeladmin, request, queryset):
    """Change the status of selected orders from open to arranged"""
    
    # Only Lab or Order Manager can use this action
    if not (request.user.groups.filter(name='Lab manager').exists() or request.user.groups.filter(name='Order manager').exists()):
        messages.error(request, 'Nice try, you are not allowed to do that.')
        return
    else:
        for order in queryset.filter(status = "open"):
            order.status = 'arranged'
            order.save()
change_order_status_to_arranged.short_description = "Change STATUS of selected to ARRANGED"
change_order_status_to_arranged.acts_on_all = True

def change_order_status_to_delivered(modeladmin, request, queryset):
    """Change the status of selected orders from arranged to delivered"""
    
    # Only Lab or Order Manager can use this action
    if not (request.user.groups.filter(name='Lab manager').exists() or request.user.groups.filter(name='Order manager').exists()):
        messages.error(request, 'Nice try, you are not allowed to do that.')
        return
    else:
        for order in queryset.filter(status = "arranged"):
            order.status = 'delivered'
            order.delivered_date = datetime.date.today()
            
            # If an order does not have a delivery date and its status changes
            # to 'delivered', set the date for delivered_date to the current
            # date. If somebody requested a delivery notification, send it and
            # set sent_email to true to remember that an email has already been 
            # sent out
            if order.delivery_alert:
                if not order.sent_email:
                    order.sent_email = True
                    message = """Dear {},

                    your order #{} for {} has just been delivered.

                    Regards,
                    The {}

                    """.format(order.created_by.first_name, order.pk, order.part_description, SITE_TITLE)
                    
                    message = inspect.cleandoc(message)
                    send_mail('Delivery notification', 
                    message, 
                    SERVER_EMAIL_ADDRESS,
                    [order.created_by.email],
                    fail_silently=True)
            order.save()

change_order_status_to_delivered.short_description = "Change STATUS of selected to DELIVERED"

def change_order_status_to_used_up(modeladmin, request, queryset):
    """Change the status of selected orders from delivered to used up"""
    
    # Only Lab or Order Manager can use this action
    if not (request.user.groups.filter(name='Lab manager').exists() or request.user.groups.filter(name='Order manager').exists()):
        messages.error(request, 'Nice try, you are not allowed to do that.')
        return
    else:
        for order in queryset.filter(status = "delivered"):
            order.status = 'used up'
            order.save()
change_order_status_to_used_up.short_description = "Change STATUS of selected to USED UP"

def export_chemicals(modeladmin, request, queryset):
    """Export all chemicals. A chemical is defines as an order
    which has a non-null ghs_pictogram_old field and is not used up"""

    queryset = Order.objects.exclude(status="used up").filter(ghs_symbols__code__isnull=False).order_by('-id')
    export_data = OrderChemicalExportResource().export(queryset)

    file_format = request.POST.get('format', default='xlsx')

    if file_format == 'xlsx':
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="{}_{}_{}.xlsx'.format(queryset.model.__name__, time.strftime("%Y%m%d"), time.strftime("%H%M%S"))
        response.write(export_data.xlsx)
    elif file_format == 'tsv':
        response = HttpResponse(content_type='text/tab-separated-values')
        response['Content-Disposition'] = 'attachment; filename="{}_{}_{}.tsv'.format(queryset.model.__name__, time.strftime("%Y%m%d"), time.strftime("%H%M%S"))
        xlsx_file = xlrd.open_workbook(file_contents=export_data.xlsx)
        sheet = xlsx_file.sheet_by_index(0)
        wr = csv.writer(response, delimiter="\t")
        for rownum in range(sheet.nrows):
            row_values = [str(i).replace("\n", "").replace('\r', '').replace("\t", "") for i in sheet.row_values(rownum)]
            wr.writerow(row_values)
    return response
export_chemicals.short_description = "Export all chemicals"

def export_orders(modeladmin, request, queryset):
    """Export orders"""

    export_data = OrderExportResource().export(queryset)

    file_format = request.POST.get('format', default='xlsx')

    if file_format == 'xlsx':
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="{}_{}_{}.xlsx'.format(queryset.model.__name__, time.strftime("%Y%m%d"), time.strftime("%H%M%S"))
        response.write(export_data.xlsx)
    elif file_format == 'tsv':
        response = HttpResponse(content_type='text/tab-separated-values')
        response['Content-Disposition'] = 'attachment; filename="{}_{}_{}.tsv'.format(queryset.model.__name__, time.strftime("%Y%m%d"), time.strftime("%H%M%S"))
        xlsx_file = xlrd.open_workbook(file_contents=export_data.xlsx)
        sheet = xlsx_file.sheet_by_index(0)
        wr = csv.writer(response, delimiter="\t")
        for rownum in range(sheet.nrows):
            row_values = [str(i).replace("\n", "").replace('\r', '').replace("\t", "") for i in sheet.row_values(rownum)]
            wr.writerow(row_values)
    return response
export_orders.short_description = "Export selected orders"

#################################################
#                 ORDER PAGES                   #
#################################################

class SearchFieldOptLocation(StrField):
    """Create a list of unique locations for search"""

    name = 'location'
    model = Location
    suggest_options = True

    def get_options(self, search):
        return self.model.objects.filter(name__icontains=search).all().order_by('name').\
        values_list('name', flat=True)

    def get_lookup_name(self):
        return 'location__name'

class SearchFieldOptCostUnit(StrField):
    """Create a list of unique cost units for search"""

    model = CostUnit
    name = 'cost_unit'
    suggest_options = True

    def get_options(self, search):
        return self.model.objects.filter(name__icontains=search).order_by('name').\
        values_list('name', flat=True)

    def get_lookup_name(self):
        return 'cost_unit__name'

class SearchFieldOptSupplier(StrField):
    """Create a list of unique cost units for search"""

    model = Order
    name = 'supplier'
    suggest_options = True

    def get_options(self, search):

        if len(search) < 3:
            return ["Type 3 or more characters to see suggestions"]
        else:
            return self.model.objects.filter(supplier__icontains=search).\
                        distinct()[:10].values_list(self.name, flat=True)

class SearchFieldOptPartDescription(StrField):
    """Create a list of unique cost units for search"""

    model = Order
    name = 'part_description'
    suggest_options = True

    def get_options(self, search):

        if len(search) < 3:
            return ["Type 3 or more characters to see suggestions"]
        else:
            return self.model.objects.filter(part_description__icontains=search).\
                distinct()[:10].values_list(self.name, flat=True)

class SearchFieldOptAzardousPregnancy(StrField):
    """Create a list of unique cost units for search"""

    model = Order
    name = 'hazard_level_pregnancy'
    suggest_options = True

class SearchFieldOptUsernameOrder(SearchFieldOptUsername):
    """Create a list of unique users' usernames for search"""

    id_list = Order.objects.all().values_list('created_by', flat=True).distinct()

class SearchFieldOptLastnameOrder(SearchFieldOptLastname):
    """Create a list of unique users' usernames for search"""

    id_list = Order.objects.all().values_list('created_by', flat=True).distinct()

class SearchFieldOptGhsSymbol(StrField):
    """Create a list of unique cost units for search"""

    model = GhsSymbol
    name = 'ghs_symbols'
    suggest_options = True

    def get_options(self, search):
        return self.model.objects.filter(code__icontains=search).order_by('code').\
        values_list('code', flat=True)

    def get_lookup_name(self):
        return 'ghs_symbols__code'

class SearchFieldOptSignalWord(StrField):
    """Create a list of unique cost units for search"""

    model = SignalWord
    name = 'signal_words'
    suggest_options = True

    def get_options(self, search):
        return self.model.objects.filter(signal_word__icontains=search).order_by('signal_word').\
        values_list('signal_word', flat=True)

    def get_lookup_name(self):
        return 'signal_words__signal_word'

class SearchFieldOptMsdsForm(StrField):
    """Create a list of unique cost units for search"""

    model = MsdsForm
    name = 'msds_form'
    suggest_options = True

    def get_options(self, search):
        return [ n[26:] for n in self.model.objects.filter(name__icontains=search).order_by('name').\
        values_list('name', flat=True)[:10]]

    def get_lookup_name(self):
        return 'msds_form__name'

class OrderQLSchema(DjangoQLSchema):
    '''Customize search functionality'''
    
    include = (Order, User, CostUnit, Location) # Include only the relevant models to be searched

    suggest_options = {
        Order: ['status', 'supplier', 'urgent'],
    }

    def get_fields(self, model):
        ''' Define fields that can be searched'''
        
        if model == Order:
            return ['id', SearchFieldOptSupplier() ,'supplier_part_no', 'internal_order_no', 
            SearchFieldOptPartDescription(), SearchFieldOptCostUnit(), 'status', 'urgent', 
            SearchFieldOptLocation(), 'comment', 'delivered_date', 'cas_number', 
            SearchFieldOptGhsSymbol(), SearchFieldOptSignalWord(), SearchFieldOptMsdsForm(), 
            SearchFieldOptAzardousPregnancy(), 'created_date_time', 'last_changed_date_time', 
            'created_by',]
        elif model == User:
            return [SearchFieldOptUsernameOrder(), SearchFieldOptLastnameOrder()]
        return super(OrderQLSchema, self).get_fields(model)

class MyMassUpdateOrderForm(MassUpdateForm):
    
    _clean = None
    _validate = None

    class Meta:
        model = Order
        fields = ['supplier','supplier_part_no', 'internal_order_no', 'part_description', 'quantity', 
            'price', 'cost_unit', 'location', 'comment', 'url', 'cas_number', "ghs_symbols", 'signal_words', 
            'msds_form', 'hazard_level_pregnancy']
    
    def clean__validate(self):
        return True
    
    def clean__clean(self):
        return False

from .models import GhsSymbol

class GhsImageWidget(AdminFileWidget):
    """
    A custom widget that displays GHS pictograms in a change_view
    """
    def render(self, name, value, attrs=None, renderer=None):

        output = []
        try:
            ghs_ids = literal_eval(value)
        except:
            ghs_ids = []
        if ghs_ids:
            for ghs_pict in GhsSymbol.objects.filter(id__in=ghs_ids):
                output.append('<img style="max-height:100px; padding-right:10px;" src="{}" />'.format(ghs_pict.pictogram.url))
            
        return mark_safe(u''.join(output))

class OrderForm(forms.ModelForm):

    """Specify a custom order form that contains a custom field to show GHS pictograms
    using GhsImageWidget"""

    ghs_pict_img = forms.FileField(label="", widget=GhsImageWidget)

    class Meta:
        model = Order
        fields = "__all__"

class OrderPage(DjangoQLSearchMixin, SimpleHistoryWithSummaryAdmin, admin.ModelAdmin):
    
    list_display = ('custom_internal_order_no', 'item_description', 'supplier_and_part_no', 'quantity', 'trimmed_comment' ,'location', 'msds_link', 'coloured_status', "created_by")
    list_display_links = ('custom_internal_order_no', )
    list_per_page = 25
    inlines = [OrderExtraDocInline, AddOrderExtraDocInline]
    djangoql_schema = OrderQLSchema
    djangoql_completion_enabled_by_default = False
    mass_update_form = MyMassUpdateOrderForm
    actions = [change_order_status_to_arranged, change_order_status_to_delivered, change_order_status_to_used_up, export_orders, export_chemicals, mass_update]
    search_fields = ['id', 'part_description', 'supplier_part_no']
    form = OrderForm
    raw_id_fields = ["ghs_symbols", 'msds_form', 'signal_words']
    autocomplete_fields = []

    def get_form(self, request, obj=None, **kwargs):
        
        form = super(OrderPage, self).get_form(request, obj, **kwargs)

        # Set the value of the custom ghs_pict_img field when an order exists otherwise
        # remove field
        if obj:
            form.base_fields['ghs_pict_img'].initial = str(list(obj.ghs_symbols.filter(pictogram__isnull=False).values_list('id', flat=True)) if obj.ghs_symbols.all().exists() else [])
        else:
            form.base_fields.pop('ghs_pict_img')
        return form

    def save_model(self, request, obj, form, change):
        
        if obj.pk == None:

            # New orders

            # If an order is new, assign the request user to it only if the order's created_by
            # attribute is not null

            obj.id = Order.objects.order_by('-id').first().id + 1 if Order.objects.exists() else 1

            try:
                obj.created_by
            except:
                obj.created_by = request.user

            obj.save()
            
            # Automatically create internal_order_number and add it to record
            if not obj.internal_order_no:
                obj.internal_order_no = "{}-{}".format(obj.pk, datetime.date.today().strftime("%y%m%d"))
            
            obj.save()
            
            # Delete first history record, which doesn't contain an internal_order_number, and change the newer history 
            # record's history_type from changed (~) to created (+). This gets rid of a duplicate history record created
            # when automatically generating an internal_order_number
            obj.history.last().delete()
            history_obj = obj.history.first()
            history_obj.history_type = "+"
            history_obj.save()
            
            # Add approval record
            if not request.user.labuser.is_principal_investigator:
                obj.approval.create(activity_type='created', activity_user=obj.history.latest().created_by)
                Order.objects.filter(id=obj.pk).update(created_approval_by_pi=True)

            # Send email to Lab Managers if an order is set as urgent
            if obj.urgent:

                # If MS Teams webhook exists, send urgent order notification to it, if not send email

                general_setting = GeneralSetting.objects.all().first()
                post_message_status_code = 0

                if general_setting.ms_teams_webhook:

                    try:
                    
                        message_card = {
                                        "@context": "https://schema.org/extensions",
                                        "@type": "MessageCard",
                                        "text": "A new urgent order has been submited",
                                        "potentialAction": [
                                            {
                                                "@type": "OpenUri",
                                                "name": "View order",
                                                "targets": [
                                                    {
                                                        "os": "default",
                                                        "uri": "https://{}/order_management/order/{}/change/".format(ALLOWED_HOSTS[0], obj.id)
                                                    }
                                                ]
                                            }
                                        ],
                                        "sections": [
                                            {
                                                "facts": [
                                                    {
                                                        "name": "Created By:",
                                                        "value": "{} {}".format(request.user.first_name, request.user.last_name)
                                                    },
                                                    {
                                                        "name": "Item:",
                                                        "value": "{} {} - {}".format(obj.supplier, obj.supplier_part_no, obj.part_description)
                                                    },
                                                    {
                                                        "name": "On/at:",
                                                        "value": datetime.datetime.strftime(timezone.localtime(obj.created_date_time, pytz.timezone(TIME_ZONE)), '%d.%m.%Y %H:%m')
                                                    }
                                                ]
                                            }
                                        ],
                                        "title": "New urgent order"
                                    }

                        post_message = requests.post(url=general_setting.ms_teams_webhook, json=message_card)
                        post_message_status_code = post_message.status_code

                    except:
                        pass

                if post_message_status_code != 200:
                    message = """Dear lab manager(s),

                    {} {} has just placed an urgent order for {} {} - {}.

                    Regards,
                    The {}

                    """.format(request.user.first_name, request.user.last_name, obj.supplier, obj.supplier_part_no, obj.part_description, SITE_TITLE)
                    message = inspect.cleandoc(message)
                
                    try:
                        
                        send_mail('New urgent order', 
                                message, 
                                    SERVER_EMAIL_ADDRESS,
                                [   general_setting.order_email_addresses],
                                    fail_silently=False,)
                        messages.success(request, 'The lab managers have been informed of your urgent order.')

                    except:
                        messages.warning(request, 'Your urgent order was added to the Order list. However, the lab managers have not been informed of it.')
            
        else:
            
            # Existing orders
            
            # Allow only Lab and Order managers to change an order
            if not (request.user.groups.filter(name='Lab manager').exists() or request.user.groups.filter(name='Order manager').exists()):
                raise PermissionDenied
            
            else:
                order = Order.objects.get(pk=obj.pk)
                
                # If the status of an order changes to the following
                if obj.status != order.status:
                    if not order.order_manager_created_date_time:
                        
                        # If an order's status changed from 'submitted' to any other, 
                        # set the date-time for order_manager_created_date_time to the
                        # current date-time
                        if obj.status in ['open', 'arranged', 'delivered']:
                            obj.order_manager_created_date_time = timezone.now()
                    
                    # If an order does not have a delivery date and its status changes
                    # to 'delivered', set the date for delivered_date to the current
                    # date. If somebody requested a delivery notification, send it and
                    # set sent_email to true to remember that an email has already been 
                    # sent out
                    if not order.delivered_date:
                        if obj.status == "delivered":
                            obj.delivered_date = datetime.date.today()
                            if order.delivery_alert:
                                if not order.sent_email:
                                    obj.sent_email = True
                                    message = """Dear {},

                                    your order #{} for {} has just been delivered.

                                    Regards,
                                    The {}

                                    """.format(obj.created_by.first_name, obj.pk, obj.part_description, SITE_TITLE)
                                    
                                    message = inspect.cleandoc(message)
                                    try:
                                        send_mail('Delivery notification', 
                                        message, 
                                        SERVER_EMAIL_ADDRESS,
                                        [obj.created_by.email],
                                        fail_silently=False,)
                                        messages.success(request, 'Delivery notification was sent.')
                                    except:
                                        messages.warning(request, 'Could not send delivery notification.')
            obj.save()
            
            # Delete order history for used-up or cancelled items
            if obj.status in ["used up", 'cancelled'] and obj.history.exists():
                obj_history = obj.history.all()
                obj_history.delete()

    def save_related(self, request, form, formsets, change):
        
        super(OrderPage, self).save_related(request, form, formsets, change)

        obj = Order.objects.get(pk=form.instance.id)

        # Keep a record of the IDs of linked M2M fields in the main order record
        # Not pretty, but it works

        obj.history_ghs_symbols = str(tuple(obj.ghs_symbols.all().order_by('code').values_list('code', flat=True))).replace(',)', ')') if obj.ghs_symbols.all() else ""
        obj.history_signal_words = str(tuple(obj.signal_words.all().order_by('signal_word').values_list('signal_word', flat=True))).replace(',)', ')') if obj.signal_words.all() else ""
        obj.ghs_symbols_autocomplete = str(tuple(obj.ghs_symbols.all().order_by('id').values_list('id', flat=True))).replace(',)', ')').replace(" ", "")[1:-1] if obj.ghs_symbols.all() else ""
        obj.signal_words_autocomplete = str(tuple(obj.signal_words.all().order_by('id').values_list('id', flat=True))).replace(',)', ')').replace(" ", "")[1:-1] if obj.signal_words.all() else ""

        obj.save()

        # Keep a record of the IDs of linked M2M fields in the latest history order record
        history_obj = obj.history.latest()
        history_obj.history_ghs_symbols = obj.history_ghs_symbols
        history_obj.history_signal_words = obj.history_signal_words
        history_obj.ghs_symbols_autocomplete = obj.ghs_symbols_autocomplete
        history_obj.signal_words_autocomplete = obj.signal_words_autocomplete

        history_obj.save()

    def get_queryset(self, request):
        
        # Allows sorting of custom changelist_view fields by adding admin_order_field
        # property to said custom field, also excludes cancelled orders, to make things prettier"""

        qs = super(OrderPage, self).get_queryset(request)
        qs = qs.annotate(models.Count('id'), models.Count('part_description'), models.Count('status'))
        
        if not (request.user.groups.filter(name='Lab manager').exists() or request.user.groups.filter(name='Order manager').exists() or request.user.is_superuser):
            return qs.exclude(status='cancelled')
        else:
            return qs

    def get_readonly_fields(self, request, obj=None):
        
        # Specifies which fields should be shown as read-only and when
        
        if obj:
            if self.can_change:
                return ['urgent', 'delivery_alert', 'delivered_date', 'order_manager_created_date_time',
                'created_date_time', 'last_changed_date_time',]
            else:
                return ['supplier','supplier_part_no', 'internal_order_no', 'part_description', 'quantity', 
            'price', 'cost_unit', 'status', 'urgent', 'delivery_alert', 'location', 'comment', 'url', 
            'delivered_date', 'cas_number', "ghs_symbols", 'signal_words', 'msds_form', 
            'hazard_level_pregnancy', 'order_manager_created_date_time', 'created_date_time', 
            'last_changed_date_time', 'created_by',]
        else:
            return ['order_manager_created_date_time', 'created_date_time',  'last_changed_date_time',]

    def add_view(self, request, extra_context=None):
        
        # Specifies which fields should be shown in the add view

        self.raw_id_fields = ["ghs_symbols", 'msds_form', 'signal_words']
        self.autocomplete_fields = []

        if request.user.groups.filter(name='Lab manager').exists() or request.user.groups.filter(name='Order manager').exists() or request.user.is_superuser:            

            self.fieldsets = (
                (None, {
                'fields': ('internal_order_no', 'supplier','supplier_part_no', 'part_description', 'quantity', 
            'price', 'cost_unit', 'status', 'urgent', 'delivery_alert', 'location', 'comment', 
            'url', 'created_by')
                    }),
                    ('SAFETY INFORMATION', {
                        'classes': ('collapse',),
                        'fields': ('cas_number', "ghs_symbols", 'signal_words', 'msds_form', 
                        'hazard_level_pregnancy',)
                        }),
                    )

        else:

            self.fieldsets = (
                (None, {
                'fields': ('supplier','supplier_part_no', 'part_description', 'quantity', 'price', 
                'cost_unit', 'urgent', 'delivery_alert', 'location', 'comment', 'url',)
                    }),
                    ('SAFETY INFORMATION', {
                        'classes': ('collapse',),
                        'fields': ('cas_number', "ghs_symbols", 'signal_words', 'msds_form', 
                        'hazard_level_pregnancy',)
                        }),
                    )
                    
        return super(OrderPage,self).add_view(request, extra_context=extra_context)

    def change_view(self, request, object_id, extra_context=None):
        
        # Specifies which fields should be shown in the change view
        
        self.can_change = False

        if object_id:
            self.autocomplete_fields = ["ghs_symbols", 'msds_form', 'signal_words']
            self.raw_id_fields = []
            
            extra_context = extra_context or {}


            self.fieldsets = (
                (None, {
                'fields': ('internal_order_no', 'supplier','supplier_part_no', 'part_description',
                'quantity', 'price', 'cost_unit', 'status', 'urgent', 'delivery_alert', 'location', 
                'comment', 'url', 'created_date_time', 'order_manager_created_date_time', 
                'delivered_date', 'created_by',)
                    }),
                    ('SAFETY INFORMATION', {
                        'fields': ('cas_number', 'ghs_symbols', 'ghs_pict_img', 
                        'signal_words', 'msds_form', 'hazard_level_pregnancy',)
                        }),
                    )

            if request.user.groups.filter(name='Lab manager').exists() or request.user.groups.filter(name='Order manager').exists() or request.user.is_superuser:

                self.can_change = True

                extra_context = {'show_close': True,
                            'show_save_and_add_another': True,
                            'show_save_and_continue': True,
                            'show_save_as_new': False,
                            'show_save': True
                            }
 
            else:
                
                extra_context = {'show_close': True,
                            'show_save_and_add_another': False,
                            'show_save_and_continue': False,
                            'show_save_as_new': False,
                            'show_save': False
                            }
        
        else:
            self.autocomplete_fields = []
            self.raw_id_fields = ["ghs_symbols", 'msds_form', 'signal_words']

        return super(OrderPage,self).change_view(request, object_id, extra_context=extra_context)
    
    def changelist_view(self, request, extra_context=None):
        
        # Set queryset of action export_chemicals to all orders

        if 'action' in request.POST and request.POST['action'] == 'export_chemicals':
            if not request.POST.getlist(admin.helpers.ACTION_CHECKBOX_NAME):
                post = request.POST.copy()
                for u in Order.objects.all():
                    post.update({admin.helpers.ACTION_CHECKBOX_NAME: str(u.id)})
                request._set_post(post)
        
        return super(OrderPage, self).changelist_view(request, extra_context=extra_context)

    def get_formsets_with_inlines(self, request, obj=None):
        
        # Remove AddOrderExtraDocInline from add/change form if user who
        # created an Order object is not the request user a Lab manager
        # or a superuser
        
        if obj:
            for inline in self.get_inline_instances(request, obj):
                if inline.verbose_name_plural == 'Existing extra docs':
                    yield inline.get_formset(request, obj), inline
                else:
                    if request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user.groups.filter(name='Order manager').exists():
                        yield inline.get_formset(request, obj), inline
        else:
            for inline in self.get_inline_instances(request, obj):
                if inline.verbose_name_plural == 'Existing extra docs':
                    continue
                else:
                    yield inline.get_formset(request, obj), inline
    
    def item_description(self, instance):
        '''Custom item description field for changelist_view'''

        part_description = instance.part_description.strip()
        part_description = part_description #[:50] + "..." if len(part_description) > 50 else part_description
        if instance.status != "cancelled":  
            return part_description
        else:
            return mark_safe('<span style="text-decoration: line-through;">{}</span>'.format(part_description))
    item_description.short_description = 'Part description'
    item_description.admin_order_field = 'part_description'

    def supplier_and_part_no(self, instance):
        '''Custom supplier and part number field for changelist_view'''

        supplier = instance.supplier.strip() if instance.supplier.lower() != "none" else ""
        for string in ["GmbH", 'Chemie']:
            supplier = supplier.replace(string, "").strip()
        supplier_part_no = instance.supplier_part_no.strip() if instance.supplier_part_no  != "none" else ""
        if instance.status != "cancelled":  
            if supplier_part_no:
                return '{} - {}'.format(supplier, supplier_part_no)
            else:
                return '{}'.format(supplier)
        else:
            if supplier_part_no:
                return mark_safe('<span style="text-decoration: line-through;">{} - {}</span>'.format(supplier, supplier_part_no))
            else:
                return mark_safe('<span style="text-decoration: line-through;">{}</span>'.format(supplier))
    supplier_and_part_no.short_description = 'Supplier - Part no.'

    def coloured_status(self, instance):
        '''Custom coloured status field for changelist_view'''

        status = "urgent" if instance.urgent and instance.status == "submitted" else instance.status

        commont_tag = '<span class="order-status" style="background-color:{};{};">{}</span>'

        styles = {  "submitted": ["#F5B041", "border: 2px solid #8F4A00;"],
                    "open": ["#F9E79F", "border: 2px solid #938139;"],
                    "arranged": ["#ABEBC6", "border: 2px solid #458560;"],
                    "delivered": ["#D5D8DC", "border: 2px solid #6F7276;"],
                    "cancelled": ["#000000", "color:white; border: 2px solid #C4C4C4;"],
                    "used up": ["#FFFFFF", "border: 2px solid #7F7F7F;"],
                    "urgent": ["#F5B7B1", "border: 2px solid #8F514B;"]}

        background_color, other_style = styles[status]

        message_status = instance.delivered_date.strftime('%d.%m.%Y') if instance.delivered_date and status != "used up" else status.capitalize()

        return mark_safe(commont_tag.format(background_color, other_style, message_status))

    coloured_status.short_description = 'Status'
    coloured_status.admin_order_field = 'status'

    def trimmed_comment(self, instance):
        '''Custom comment field for changelist_view'''

        comment = instance.comment
        if comment: 
            return comment[:65] + "..." if len(comment) > 65 else comment
        else:
            None
    trimmed_comment.short_description = 'Comments'
    
    def msds_link (self, instance):
        '''Custom comment field for changelist_view'''
        
        if instance.msds_form:
            return mark_safe('<a class="magnificent" href="{0}">View</a>'.format(instance.msds_form.name.url))
        else:
            None
    msds_link.short_description = 'MSDS'

    def custom_internal_order_no (self, instance):
        '''Custom internal order no field for changelist_view'''

        if str(instance.internal_order_no).startswith(str(instance.id)):
            return mark_safe('<span style="white-space: nowrap;">{}</span>'.format(instance.internal_order_no))
        else:
            return str(instance.id)
    
    custom_internal_order_no.short_description = "ID"
    custom_internal_order_no.admin_order_field = 'id'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        
        try:
            request.resolver_match.args[0]
        except:
            
            # Exclude certain users from the 'Created by' field in the order form

            if db_field.name == 'created_by':
                if request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user.groups.filter(name='Order manager').exists():
                    kwargs["queryset"] = User.objects.exclude(id__in=[1, 20, 36]).order_by('last_name')
                kwargs['initial'] = request.user.id

            # Sort cost_unit and locations fields by name
            
            if db_field.name == "cost_unit":
                kwargs["queryset"] = CostUnit.objects.exclude(status=True).order_by('name')

            if db_field.name == "location":
                kwargs["queryset"] = Location.objects.exclude(status=True).order_by('name')

        return super(OrderPage, self).formfield_for_foreignkey(db_field, request, **kwargs)

#################################################
#                MSDS FORM PAGES                #
#################################################

class SearchFieldOptMsdsName(StrField):
    """Create a list of unique cost units for search"""

    model = MsdsForm
    name = 'name'
    suggest_options = True

    def get_options(self, search):
        return self.model.objects.all().distinct()

class MsdsFormQLSchema(DjangoQLSchema):
    '''Customize search functionality'''
    
    def get_fields(self, model):
        ''' Define fields that can be searched'''
        
        if model == MsdsForm:
            return ['id', SearchFieldOptMsdsName()]
        return super(MsdsFormQLSchema, self).get_fields(model)

class MsdsFormForm(forms.ModelForm):
    def clean_name(self):
        
        # Check if the name of a MSDS form is unique before saving
        
        qs = MsdsForm.objects.filter(name__icontains=self.cleaned_data["name"].name)
        if qs.exists():
            raise forms.ValidationError('A form with this name already exists.')
        else:
            return self.cleaned_data["name"]

class MsdsFormPage(DjangoQLSearchMixin, admin.ModelAdmin):
    
    list_display = ('id', 'pretty_file_name', 'view_file_link')
    list_per_page = 25
    ordering = ['name']
    djangoql_schema = MsdsFormQLSchema
    djangoql_completion_enabled_by_default = False
    search_fields = ['id', 'name']
    form = MsdsFormForm
    
    def add_view(self,request,extra_context=None):
        self.fields = (['name',])
        return super(MsdsFormPage,self).add_view(request)

    def change_view(self,request,object_id,extra_context=None):
        self.fields = (['name',])
        return super(MsdsFormPage,self).change_view(request,object_id)

    def pretty_file_name(self, instance):
        '''Custom file name field for changelist_view'''
        from os.path import basename
        short_name = basename(instance.name.name).split('.')
        short_name = ".".join(short_name[:-1]).replace("_", " ")
        return(short_name)
    pretty_file_name.short_description = "File name"
    pretty_file_name.admin_order_field = 'name'

    def view_file_link(self, instance):
        '''Custom field which shows the url of a MSDS form as a HTML <a> tag with 
        text View'''
        return(mark_safe('<a class="magnificent" href="{}">{}</a>'.format(instance.name.url, "View")))
    view_file_link.short_description = ""

#################################################
#            ORDER EXTRA DOC PAGES              #
#################################################

class OrderExtraDocPage(DjangoQLSearchMixin, admin.ModelAdmin):
    list_display = ('id','name',)
    list_display_links = ('id','name', )
    list_per_page = 25
    ordering = ['id']

    def has_module_permission(self, request):
        
        # Hide module from Admin
        return False

    def get_readonly_fields(self, request, obj=None):
        
        # Specifies which fields should be shown as read-only and when

        if obj:
            return ['name', 'order', 'created_date_time',]
    
    def add_view(self,request,extra_context=None):

        # Specifies which fields should be shown in the add view
        self.fields = (['name', 'order', 'created_date_time',])
        return super(OrderExtraDocPage,self).add_view(request)

    def change_view(self,request,object_id,extra_context=None):
        
        # Specifies which fields should be shown in the change view
        self.fields = (['name', 'order', 'created_date_time',])
        return super(OrderExtraDocPage,self).change_view(request,object_id)

#################################################
#           ORDER COST UNIT PAGES               #
#################################################

class CostUnitPage(admin.ModelAdmin):
    
    list_display = ('name', 'description', 'status')
    list_display_links = ('name',)
    list_per_page = 25
    ordering = ['name']

#################################################
#           ORDER LOCATION PAGES                #
#################################################

class LocationPage(admin.ModelAdmin):
    
    list_display = ('name', 'status')
    list_display_links = ('name', )
    list_per_page = 25
    ordering = ['name']

#################################################
#              GHS SYMBOL PAGES                 #
#################################################

class GhsSymbolPage(admin.ModelAdmin):
    
    list_display = ('code', 'pictogram_img', 'description')
    list_display_links = ('code', )
    list_per_page = 25
    ordering = ['code']
    search_fields = ['code']

    def pictogram_img(self, instance):
        '''Custom field which shows the a GHS symbol'''
        return(mark_safe('<img style="max-height:60px;" src="{}" />'.format(instance.pictogram.url,)))
    pictogram_img.short_description = "Pictogram"

#################################################
#              SIGNAL WORD PAGES                #
#################################################

class SignalWordPage(admin.ModelAdmin):
    
    list_display = ('signal_word', )
    list_display_links = ('signal_word', )
    list_per_page = 25
    ordering = ['signal_word']
    search_fields = ['signal_word']