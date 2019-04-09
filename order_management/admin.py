# -*- coding: utf-8 -*-

from __future__ import unicode_literals

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

#################################################
#        ADDED FUNCTIONALITIES IMPORTS          #
#################################################

# Advanced search functionalities from DjangoQL
from djangoql.admin import DjangoQLSearchMixin
from djangoql.schema import DjangoQLSchema, StrField
from collection_management.admin import SearchFieldOptUsername, SearchFieldOptLastname

# Object history tracking from django-simple-history
from simple_history.admin import SimpleHistoryAdmin
from collection_management.admin import SimpleHistoryWithSummaryAdmin

# Import/Export functionalities from django-import-export
from import_export.admin import ExportActionModelAdmin

# Background tasks
from background_task import background

# Mass update
from adminactions.mass_update import *

#################################################
#                OTHER IMPORTS                  #
#################################################

from .models import OrderExtraDoc as order_management_OrderExtraDoc
from .models import Order as order_management_Order
from .models import Location as order_management_Location
from .models import CostUnit as order_management_CostUnit
from .models import OrderExtraDoc as order_management_OrderExtraDoc
from .models import MsdsForm as order_management_MsdsForm

import datetime
import time
import inspect

#################################################
#               CUSTOM FUNCTIONS                #
#################################################

@background(schedule=60) # Run update_autocomplete_js 1 min after it is called, as "background" process
def update_autocomplete_js():
    """Updates product-autocomplete.js file with unique products from the order database
    to supply information to the autocomplete function of the order add page"""

    from django_project.settings import BASE_DIR

    header_js = "$(function(){var product_names = ["

    # Loop through all the elements (= rows) in the order list
    jsonlin = ""
    lstofprodname = []
    
    for order in order_management_Order.objects.all().order_by('-id').values("supplier", "supplier_part_no", "part_description", "location", "msds_form", "price", "cas_number", "ghs_pictogram"):
        
        # Output specific order field to file new order form's autocomplete functionality
        part_description_lower = order["part_description"].lower()
        supplier_part_no = order["supplier_part_no"].strip().replace('#'," ")
        if (part_description_lower not in lstofprodname) and (part_description_lower != "none"):
            if (len(supplier_part_no)>0) and ("?" not in supplier_part_no) :
                jsonlin = jsonlin + '{{value:"{}",data:"{}#{}#{}#{}#{}#{}#{}"}},'.format(
                    order["part_description"], 
                    supplier_part_no, 
                    order["supplier"], 
                    order["location"],
                    order["msds_form"] if order["msds_form"] else 0,
                    order["price"],
                    order["cas_number"], 
                    order["ghs_pictogram"])
                lstofprodname.append(part_description_lower)

    footer_js = """];$('#id_part_description').autocomplete({source: function(request, response){var results =\
    $.ui.autocomplete.filter(product_names, request.term);response(results.slice(0, 10));},select: function(e,\
    ui){var extra_data = ui.item.data.split('#');\
    $('#id_supplier_part_no').val(extra_data[0]);\
    $('#id_supplier').val(extra_data[1]);\
    $('#id_location').val(extra_data[2]);\
    if (extra_data[3] != "0"){$('#id_msds_form').val(extra_data[3])} else {$('#id_msds_form').val(null)};\
    if (extra_data[4] != ""){$('#id_price').val(extra_data[4])} else {$('#id_price').val(null)};\
    if (extra_data[5] != ""){$('#id_cas_number').val(extra_data[5])} else {$('#id_cas_number').val(null)};\
    if (extra_data[6] != ""){$('#id_ghs_pictogram').val(extra_data[6])} else {$('#id_ghs_pictogram').val(null)};\
    }});\
    });"""
    
    with open(BASE_DIR + "/static/admin/js/order_management/product-autocomplete.js","w") as out_handle_js:
        out_handle_js.write(header_js + jsonlin + footer_js)

#################################################
#         CUSTOM MASS UPDATE FUNCTION           #
#################################################

def mass_update(modeladmin, request, queryset):  # noqa
    """
        mass update queryset
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
    from django.utils.encoding import smart_text

    def not_required(field, **kwargs):
        """ force all fields as not required"""
        kwargs['required'] = False
        return field.formfield(**kwargs)

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

    MForm = modelform_factory(modeladmin.model, form=mass_update_form,
                              exclude=('pk',),
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
            validate = True
            clean = False

            if validate:
                with atomic():
                    _doit()

            else:
                values = {}
                for field_name, value in list(form.cleaned_data.items()):
                    if isinstance(form.fields[field_name], ModelMultipleChoiceField):
                        messages.error(request, "Unable to mass update ManyToManyField without 'validate'")
                        return HttpResponseRedirect(request.get_full_path())
                    elif callable(value):
                        messages.error(request, "Unable to mass update using operators without 'validate'")
                        return HttpResponseRedirect(request.get_full_path())
                    elif field_name not in ['_selected_action', '_validate', 'select_across', 'action',
                                            '_unique_transaction', '_clean']:
                        values[field_name] = value
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

    for el in queryset.all()[:10]:
        for f in modeladmin.model._meta.fields:
            if f.name not in form._no_sample_for:
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
               smart_text(modeladmin.opts.verbose_name_plural),
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

    update_autocomplete_js()

    return render(request, tpl, context=ctx)

mass_update.short_description = _("Mass update selected orders")

#################################################
#                 ORDER INLINES                 #
#################################################

class OrderExtraDocInline(admin.TabularInline):
    """Inline to view existing extra order documents"""

    model = order_management_OrderExtraDoc
    verbose_name_plural = "Existing extra docs"
    extra = 0
    fields = ['get_doc_short_name', 'description']
    readonly_fields = ['get_doc_short_name', 'description']

    def has_add_permission(self, request):
        return False
    
    def get_doc_short_name(self, instance):
        '''This function allows you to define a custom field for the list view to
        be defined in list_display as the name of the function, e.g. in this case
        list_display = ('id', 'name', 'selection', 'get_plasmidmap_short_name','created_by',)'''
        if instance.name:
            return mark_safe('<a href="{}">View</a>'.format(instance.name.url))
        else:
            return ''
    get_doc_short_name.short_description = 'Document'

class AddOrderExtraDocInline(admin.TabularInline):
    """Inline to add new extra order documents"""

    model = order_management_OrderExtraDoc
    verbose_name_plural = "New extra docs"
    extra = 0
    fields = ['name','description']

    def has_change_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        '''Override default get_readonly_fields to define user-specific read-only fields
        If a user is not a superuser, lab manager or order manager
        return all fields as read-only'''

        if obj:
            if not (request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists() or request.user.groups.filter(name='Order manager').exists()):
                return ['name','description']
            else:
                return []
        else:
            return []

#################################################
#         ORDER IMPORT/EXPORT RESOURCE          #
#################################################

from import_export import resources

class OrderChemicalExportResource(resources.ModelResource):
    """Defines a custom export resource class for chemicals"""
    class Meta:
        model = order_management_Order
        fields = ('id','supplier', 'supplier_part_no', 'part_description', 'quantity', "location__name", "cas_number", "ghs_pictogram")

class OrderExportResource(resources.ModelResource):
    """Defines a custom export resource class for orders"""
    class Meta:
        model = order_management_Order
        fields = ('id', 'internal_order_no', 'supplier', 'supplier_part_no', 'part_description', 'quantity', 
            'price', 'cost_unit__name', 'status', 'location__name', 'comment', 'url', 'delivered_date', 'cas_number', 
            'ghs_pictogram', 'created_date_time', 'order_manager_created_date_time', 'last_changed_date_time', 'created_by__username',)

#################################################
#                   ACTIONS                     #
#################################################

def status_to_arranged(modeladmin, request, queryset):
    """Change the status of selected orders from open to arranged"""
    
    if not (request.user.groups.filter(name='Lab manager').exists() or request.user.groups.filter(name='Order manager').exists()):
        messages.error(request, 'Nice try, you are not allowed to do that.')
        return
    else:
        for order in queryset.filter(status = "open"):
            order.status = 'arranged'
            order.save()
status_to_arranged.short_description = "Change STATUS of selected to ARRANGED"

def status_to_delivered(modeladmin, request, queryset):
    """Change the status of selected orders from arranged to delivered"""
    
    if not (request.user.groups.filter(name='Lab manager').exists() or request.user.groups.filter(name='Order manager').exists()):
        messages.error(request, 'Nice try, you are not allowed to do that.')
        return
    else:
        for order in queryset.filter(status = "arranged"):
            order.status = 'delivered'
            order.delivered_date = datetime.date.today()
            if order.delivery_alert:
                if not order.sent_email:
                    order.sent_email = True
                    message = """Dear {},

                    your order #{} for {} has just been delivered.

                    Regards,
                    The Ulrich lab intranet

                    """.format(order.created_by.first_name, order.pk, order.part_description)
                    
                    message = inspect.cleandoc(message)
                    send_mail('Delivery notification', 
                    message, 
                    'system@imbc2.imb.uni-mainz.de',
                    [order.created_by.email],
                    fail_silently=True)
            order.save()
status_to_delivered.short_description = "Change STATUS of selected to DELIVERED"

def status_to_used_up(modeladmin, request, queryset):
    """Change the status of selected orders from delivered to used up"""
    
    if not (request.user.groups.filter(name='Lab manager').exists() or request.user.groups.filter(name='Order manager').exists()):
        messages.error(request, 'Nice try, you are not allowed to do that.')
        return
    else:
        for order in queryset.filter(status = "delivered"):
            order.status = 'used up'
            order.save()
status_to_used_up.short_description = "Change STATUS of selected to USED UP"

def export_chemicals(modeladmin, request, queryset):
    """Export all chemicals as xlsx. A chemical is defines as an order
    which has a non-null ghs_pictogram field and is not used up"""

    queryset = order_management_Order.objects.exclude(status="used up").annotate(text_len=Length('ghs_pictogram')).filter(text_len__gt=0).order_by('-id')
    export_data = OrderChemicalExportResource().export(queryset)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="Chemicals_{}_{}.xlsx'.format(time.strftime("%Y%m%d"), time.strftime("%H%M%S"))
    response.write(export_data.xlsx)
    return response
export_chemicals.short_description = "Export chemicals as xlsx"
status_to_arranged.acts_on_all = True

def export_orders(modeladmin, request, queryset):
    """Export orders as xlsx"""

    export_data = OrderExportResource().export(queryset)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="{}_{}_{}.xlsx'.format(order_management_Order.__name__, time.strftime("%Y%m%d"), time.strftime("%H%M%S"))
    response.write(export_data.xlsx)
    return response
export_orders.short_description = "Export selected orders as xlsx"

#################################################
#                 ORDER PAGES                   #
#################################################

class SearchFieldOptLocation(StrField):
    """Create a list of unique locations for search"""

    model = order_management_Location
    name = 'name'
    suggest_options = True

    def get_options(self):
        return super(SearchFieldOptLocation, self).\
        get_options().all().order_by(self.name).\
        values_list(self.name, flat=True)

class SearchFieldOptCostUnit(StrField):
    """Create a list of unique cost units for search"""

    model = order_management_CostUnit
    name = 'name'
    suggest_options = True

    def get_options(self):
        return super(SearchFieldOptCostUnit, self).\
        get_options().all().order_by(self.name).\
        values_list(self.name, flat=True)

class SearchFieldOptSupplier(StrField):
    """Create a list of unique cost units for search"""

    model = order_management_Order
    name = 'supplier'
    suggest_options = True

    def get_options(self):
        return super(SearchFieldOptSupplier, self).\
        get_options().all().distinct()

class SearchFieldOptPartDescription(StrField):
    """Create a list of unique cost units for search"""

    model = order_management_Order
    name = 'part_description'
    suggest_options = True

    def get_options(self):
        return super(SearchFieldOptPartDescription, self).\
        get_options().all().distinct()

class OrderQLSchema(DjangoQLSchema):
    '''Customize search functionality'''
    
    include = (order_management_Order, User, order_management_CostUnit, order_management_Location) # Include only the relevant models to be searched

    suggest_options = {
        order_management_Order: ['status', 'supplier', 'urgent'],
    }

    def get_fields(self, model):
        ''' Define fields that can be searched'''
        
        if model == order_management_Order:
            return ['id', SearchFieldOptSupplier() ,'supplier_part_no', 'internal_order_no', SearchFieldOptPartDescription(), 'cost_unit', 
            'status', 'urgent', 'location', 'comment', 'delivered_date', 'cas_number', 
            'ghs_pictogram', 'msds_form', 'created_date_time', 'last_changed_date_time', 'created_by',]
        elif model == User:
            return [SearchFieldOptUsername(), SearchFieldOptLastname()]
        elif model == order_management_CostUnit:
            return [SearchFieldOptCostUnit()]
        elif model == order_management_Location:
            return [SearchFieldOptLocation()]
        return super(OrderQLSchema, self).get_fields(model)

class MyMassUpdateOrderForm(MassUpdateForm):
    
    _clean = None
    _validate = None

    class Meta:
        model = order_management_Order
        fields = ['supplier','supplier_part_no', 'internal_order_no', 'part_description', 'quantity', 
            'price', 'cost_unit', 'location', 'comment', 'url', 'cas_number', 'ghs_pictogram', 'msds_form']
        app_verbose_name = 'Test'
    
    def clean__validate(self):
        return True
    
    def clean__clean(self):
        return False

class OrderPage(DjangoQLSearchMixin, SimpleHistoryWithSummaryAdmin, admin.ModelAdmin):
    list_display = ('custom_internal_order_no', 'item_description', 'supplier_and_part_no', 'quantity', 'trimmed_comment' ,'location', 'msds_link', 'coloured_status', "created_by")
    list_display_links = ('custom_internal_order_no', )
    list_per_page = 25
    inlines = [OrderExtraDocInline, AddOrderExtraDocInline]
    djangoql_schema = OrderQLSchema
    mass_update_form = MyMassUpdateOrderForm
    actions = [status_to_arranged, status_to_delivered, status_to_used_up, export_orders, export_chemicals, mass_update]
    
    def save_model(self, request, obj, form, change):
        """Override default save_model to add some extra functionalities,
        like sending emails when required"""
        
        if obj.pk == None:
            try:
                obj.created_by
            except:
                obj.created_by = request.user
            try:
                if not order_management_Order.objects.filter(part_description=obj.part_description):
                    update_autocomplete_js()
            except:
                messages.warning(request, 'Could not update the order autocomplete function')
            obj.save()
            
            # Automatically create internal_order_number and add it to record
            obj.internal_order_no = "{}-{}".format(obj.pk, datetime.date.today().strftime("%y%m%d"))
            obj.save()
            
            # Delete first history record, which doesn't contain an internal_order_number, and change the newer history 
            # record's history_type from changed (~) to created (+). This gets rid of a duplicate history record created
            # when automatically generating an internal_order_number
            obj.history.last().delete()
            history_obj = obj.history.first()
            history_obj.history_type = "+"
            history_obj.save()

            if obj.urgent:
                message = """Dear lab managers,

                {} {} has just placed an urgent order for {} {} - {}.

                Regards,
                The Ulrich lab intranet

                """.format(request.user.first_name, request.user.last_name, obj.supplier, obj.supplier_part_no, obj.part_description)
                message = inspect.cleandoc(message)
                try:
                    send_mail('New urgent order', 
                    message, 
                    'system@imbc2.imb.uni-mainz.de',
                    ['ulrich-orders@imb-mainz.de'],
                    fail_silently=False,)
                    messages.success(request, 'The lab managers have been informed of your urgent order.')
                except:
                    messages.warning(request, 'Your urgent order was added to the Order list. However, the lab managers have not been informed of it.')
        else:
            if not (request.user.groups.filter(name='Lab manager').exists() or request.user.groups.filter(name='Order manager').exists()):
                raise PermissionDenied
            else:
                order = order_management_Order.objects.get(pk=obj.pk)
                if obj.status != order.status:
                    if not order.order_manager_created_date_time:
                        if obj.status in ['open', 'arranged', 'delivered']:
                            obj.order_manager_created_date_time = timezone.now()
                    if not order.delivered_date:
                        if obj.status == "delivered":
                            obj.delivered_date = datetime.date.today()
                            if order.delivery_alert:
                                if not order.sent_email:
                                    obj.sent_email = True
                                    message = """Dear {},

                                    your order #{} for {} has just been delivered.

                                    Regards,
                                    The Ulrich lab intranet

                                    """.format(obj.created_by.first_name, obj.pk, obj.part_description)
                                    
                                    message = inspect.cleandoc(message)
                                    try:
                                        send_mail('Delivery notification', 
                                        message, 
                                        'system@imbc2.imb.uni-mainz.de',
                                        [obj.created_by.email],
                                        fail_silently=False,)
                                        messages.success(request, 'Delivery notification was sent.')
                                    except:
                                        messages.warning(request, 'Could not send delivery notification.')
            obj.save()
            try:
                if [obj.supplier, obj.supplier_part_no, obj.part_description, obj.location, obj.msds_form, obj.price, obj.cas_number, obj.ghs_pictogram] != [order.supplier, order.supplier_part_no, order.part_description, order.location, order.msds_form, order.price, order.cas_number, order.ghs_pictogram]:
                    update_autocomplete_js()
            except:
                messages.warning(request, 'Could not update the order autocomplete function')
                
    
    def get_queryset(self, request):
        """Allows sorting of custom changelist_view fields by adding admin_order_field
        propoerty to said custom field"""

        qs = super(OrderPage, self).get_queryset(request)
        qs = qs.annotate(models.Count('id'), models.Count('part_description'), models.Count('status'))
        return qs

    def get_readonly_fields(self, request, obj=None):
        '''Override default get_readonly_fields to define user-specific read-only fields'''
        
        if obj:
            if not (request.user.groups.filter(name='Lab manager').exists() or request.user.groups.filter(name='Order manager').exists()):
                return ['supplier','supplier_part_no', 'internal_order_no', 'part_description', 'quantity', 
            'price', 'cost_unit', 'status', 'urgent', 'delivery_alert', 'location', 'comment', 'url', 'delivered_date', 'cas_number', 
            'ghs_pictogram', 'msds_form', 'order_manager_created_date_time', 'created_date_time', 'last_changed_date_time', 'created_by',]
            else:
                return ['urgent', 'delivery_alert', 'delivered_date', 'order_manager_created_date_time','created_date_time', 'last_changed_date_time',]
        else:
            return ['order_manager_created_date_time', 'created_date_time',  'last_changed_date_time',]

    def add_view(self,request,extra_content=None):
        '''Override default add_view to show only desired fields'''
        
        if request.user.groups.filter(name='Lab manager').exists() or request.user.groups.filter(name='Order manager').exists():
            self.fields = ('supplier','supplier_part_no', 'part_description', 'quantity', 
            'price', 'cost_unit', 'status', 'urgent', 'delivery_alert', 'location', 'comment', 'url', 'cas_number', 
            'ghs_pictogram', 'msds_form', 'created_by')
        else:
            self.fields = ('supplier','supplier_part_no', 'part_description', 'quantity', 'price', 'cost_unit', 'urgent',
            'delivery_alert', 'location', 'comment', 'url', 'cas_number', 'ghs_pictogram', 'msds_form')
        return super(OrderPage,self).add_view(request)

    def change_view(self,request,object_id,extra_content=None):
        '''Override default change_view to show only desired fields'''
        
        self.fields = ('supplier','supplier_part_no', 'internal_order_no', 'part_description', 'quantity', 
            'price', 'cost_unit', 'status', 'urgent', 'delivery_alert', 'location', 'comment', 'url', 'cas_number', 
            'ghs_pictogram', 'msds_form', 'created_date_time', 'order_manager_created_date_time', 'delivered_date', 'created_by',)
        return super(OrderPage,self).change_view(request,object_id)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        """Override default changeform_view to hide Save buttons when certain conditions (same as
        those in get_readonly_fields method) are met"""

        extra_context = extra_context or {}
        extra_context['show_submit_line'] = True
        if object_id:
            obj = order_management_Order.objects.get(pk=object_id)
            if obj:
                if not (request.user.groups.filter(name='Lab manager').exists() or request.user.groups.filter(name='Order manager').exists()):
                    extra_context['show_submit_line'] = False
        return super(OrderPage, self).changeform_view(request, object_id, extra_context=extra_context)
    
    def changelist_view(self, request, extra_context=None):
        """Override default changelist_view to set queryset of action export_chemicals to all orders"""

        if 'action' in request.POST and request.POST['action'] == 'export_chemicals':
            if not request.POST.getlist(admin.ACTION_CHECKBOX_NAME):
                post = request.POST.copy()
                for u in order_management_Order.objects.all():
                    post.update({admin.ACTION_CHECKBOX_NAME: str(u.id)})
                request._set_post(post)
        return super(OrderPage, self).changelist_view(request, extra_context)

    def get_formsets_with_inlines(self, request, obj=None):
        """Remove AddOrderExtraDocInline from add/change form if user who
        created an Order object is not the request user a lab manager
        or a superuser"""
        
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
        '''Define a custom item description field for changelist_view'''

        part_description = instance.part_description.strip()
        part_description = part_description[:50] + "..." if len(part_description) > 50 else part_description
        if instance.status != "cancelled":  
            return part_description
        else:
            return mark_safe('<span style="text-decoration: line-through;">{}</span>'.format(part_description))
    item_description.short_description = 'Part description'
    item_description.admin_order_field = 'part_description'

    def supplier_and_part_no(self, instance):
        '''Define a custom supplier and part number field for changelist_view'''

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
        '''Define a custom status field for changelist_view'''

        status = instance.status
        urgent = instance.urgent
        
        if status == "submitted":
            if urgent:
                return mark_safe('<span style="width:100%; height:100%; background-color:#F5B7B1;">{}</span>'.format('Urgent'))
            else:
                return mark_safe('<span style="width:100%; height:100%; background-color:#F5B041;">{}</span>'.format(status.capitalize()))
        elif status == "open":
            return mark_safe('<span style="width:100%; height:100%; background-color:#F9E79F;">{}</span>'.format(status.capitalize()))
        elif status == "arranged":
            return mark_safe('<span style="width:100%; height:100%; background-color:#ABEBC6;">{}</span>'.format(status.capitalize()))
        elif status == "delivered":
            return mark_safe('<span style="width:100%; height:100%; background-color:#D5D8DC;">{}</span>'.format(status.capitalize()))
        elif status == "cancelled":
            return mark_safe('<span style="width:100%; height:100%; background-color:#000000; color: white;">{}</span>'.format(status.capitalize()))
        elif status == "used up":
            return mark_safe('<span style="width:100%; height:100%; border-style: double;">{}</span>'.format(status.capitalize()))

    coloured_status.short_description = 'Status'
    coloured_status.admin_order_field = 'status'

    def trimmed_comment(self, instance):
        '''Define a custom comment field for changelist_view'''

        comment = instance.comment
        if comment: 
            return comment[:65] + "..." if len(comment) > 65 else comment
        else:
            None
    trimmed_comment.short_description = 'Comments'
    
    def msds_link (self, instance):
        '''Define a custom comment field for changelist_view'''
        if instance.msds_form:
            return mark_safe('<a href="{0}">View</a>'.format(instance.msds_form.name.url))
        else:
            None
    msds_link.short_description = 'MSDS'

    def custom_internal_order_no (self, instance):
        
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
            if db_field.name == 'created_by':
                if request.user.is_superuser:
                    kwargs["queryset"] = User.objects.exclude(groups__name = 'Past member').exclude(id__in=[20]).order_by('last_name')
                else:
                    kwargs["queryset"] = User.objects.exclude(groups__name = 'Past member').exclude(id__in=[1,20]).order_by('last_name')
                kwargs['initial'] = request.user.id

            if db_field.name == "cost_unit":
                kwargs["queryset"] = order_management_CostUnit.objects.exclude(status=True).order_by('name')

            if db_field.name == "location":
                kwargs["queryset"] = order_management_Location.objects.exclude(status=True).order_by('name')

        return super(OrderPage, self).formfield_for_foreignkey(db_field, request, **kwargs)

#################################################
#                MSDS FORM PAGES                #
#################################################

class SearchFieldOptMsdsName(StrField):
    """Create a list of unique cost units for search"""

    model = order_management_MsdsForm
    name = 'name'
    suggest_options = True

    def get_options(self):
        return super(SearchFieldOptMsdsName, self).\
        get_options().all().distinct()

class MsdsFormQLSchema(DjangoQLSchema):
    '''Customize search functionality'''
    
    def get_fields(self, model):
        ''' Define fields that can be searched'''
        
        if model == order_management_MsdsForm:
            return ['id', SearchFieldOptMsdsName()]
        return super(MsdsFormQLSchema, self).get_fields(model)

class MsdsFormPage(DjangoQLSearchMixin, admin.ModelAdmin):
    list_display = ('id','name',)
    list_per_page = 25
    ordering = ['name']
    djangoql_schema = MsdsFormQLSchema
    
    def add_view(self,request,extra_content=None):
        '''Override default add_view to show only desired fields'''

        self.fields = (['name',])
        return super(MsdsFormPage,self).add_view(request)

    def change_view(self,request,object_id,extra_content=None):
        '''Override default change_view to show only desired fields'''

        self.fields = (['name',])
        return super(MsdsFormPage,self).change_view(request,object_id)

#################################################
#            ORDER EXTRA DOC PAGES              #
#################################################

class OrderExtraDocPage(DjangoQLSearchMixin, admin.ModelAdmin):
    list_display = ('id','name',)
    list_display_links = ('id','name', )
    list_per_page = 25
    ordering = ['id']

    def has_module_permission(self, request):
        '''Hide module from Admin'''
        return False

    def get_readonly_fields(self, request, obj=None):
        '''Override default get_readonly_fields to define user-specific read-only fields
        If a user is not a superuser, lab manager or the user who created a record
        return all fields as read-only 
        'created_date_time' and 'last_changed_date_time' fields must always be read-only
        because their set by Django itself'''

        if obj:
            return ['name', 'order', 'created_date_time',]
    
    def add_view(self,request,extra_content=None):
        '''Override default add_view to show only desired fields'''

        self.fields = (['name', 'order', 'created_date_time',])
        return super(OrderExtraDocPage,self).add_view(request)

    def change_view(self,request,object_id,extra_content=None):
        '''Override default change_view to show only desired fields'''

        self.fields = (['name', 'order', 'created_date_time',])
        return super(OrderExtraDocPage,self).change_view(request,object_id)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        """Override default changeform_view to hide Save buttons when certain conditions (same as
        those in get_readonly_fields method) are met"""

        extra_context = extra_context or {}
        extra_context['show_submit_line'] = True
        if object_id:
            extra_context['show_submit_line'] = False
        return super(OrderExtraDocPage, self).changeform_view(request, object_id, extra_context=extra_context)

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