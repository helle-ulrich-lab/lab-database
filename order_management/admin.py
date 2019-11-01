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

from django_project.private_settings import SITE_TITLE
from django_project.private_settings import DJANGO_PRIVATE_DATA

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

# Background tasks
from background_task import background

# Mass update
from adminactions.mass_update import MassUpdateForm, get_permission_codename,\
    ActionInterrupted, adminaction_requested, adminaction_start, adminaction_end

# jsmin
from jsmin import jsmin

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
    """Updates /static/admin/js/order_management/product-autocomplete.js with info of unique 
    products from the order database. In turn, this supplies information to the autocomplete 
    function of the order add page"""

    from django_project.settings import BASE_DIR

    lstofprodname = []
    part_description_json_line = ""
    part_no_json_line = ""
    
    # Loop through all elements (= rows) in the order list
    for order in order_management_Order.objects.all().order_by('-id').values("supplier", "supplier_part_no", "part_description", "location", "msds_form", "price", "cas_number", "ghs_pictogram"):
        
        # Create value:data pairs using part_description or supplier_part_no as values
        part_description_lower = order["part_description"].lower()
        supplier_part_no = order["supplier_part_no"].strip().replace('#'," ")
        
        if (part_description_lower not in lstofprodname) and (part_description_lower != "none"):
            if (len(supplier_part_no)>0) and ("?" not in supplier_part_no) :
                
                part_description_json_line = part_description_json_line + '{{value:"{}",data:"{}#{}#{}#{}#{}#{}#{}"}},'.format(
                    order["part_description"], 
                    supplier_part_no, 
                    order["supplier"], 
                    order["location"],
                    order["msds_form"] if order["msds_form"] else 0,
                    order["price"],
                    order["cas_number"], 
                    order["ghs_pictogram"])
                
                part_no_json_line = part_no_json_line + '{{value:"{}",data:"{}#{}#{}#{}#{}#{}#{}"}},'.format(
                    supplier_part_no, 
                    order["part_description"], 
                    order["supplier"], 
                    order["location"],
                    order["msds_form"] if order["msds_form"] else 0,
                    order["price"],
                    order["cas_number"], 
                    order["ghs_pictogram"])
                
                lstofprodname.append(part_description_lower)

    header_js = """$(function(){{var product_names = [{}];\
                var supplier_part_no = [{}];""".format(part_description_json_line, part_no_json_line)

    footer_js = """$('#id_part_description').autocomplete({\
            source: function(request, response) {\
                var results = $.ui.autocomplete.filter(product_names, request.term);\
                response(results.slice(0, 10));\
            },\
            select: function(e, ui) {\
                var extra_data = ui.item.data.split('#');\
                $('#id_supplier_part_no').val(extra_data[0]);\
                $('#id_supplier').val(extra_data[1]);\
                $('#id_location').val(extra_data[2]);\
                if (extra_data[3] != "0") {\
                    $('#id_msds_form').val(extra_data[3])\
                } else {\
                    $('#id_msds_form').val(null)\
                }\
                ;if (extra_data[4] != "") {\
                    $('#id_price').val(extra_data[4])\
                } else {\
                    $('#id_price').val(null)\
                }\
                ;if (extra_data[5] != "") {\
                    $('#id_cas_number').val(extra_data[5])\
                } else {\
                    $('#id_cas_number').val(null)\
                }\
                ;if (extra_data[6] != "") {\
                    $('#id_ghs_pictogram').val(extra_data[6])\
                } else {\
                    $('#id_ghs_pictogram').val(null)\
                }\
                ;\
            }\
        });\
        $('#id_supplier_part_no').autocomplete({\
        source: function(request, response) {\
            var results = $.ui.autocomplete.filter(supplier_part_no, request.term);\
            response(results.slice(0, 10));\
        },\
        select: function(e, ui) {\
            var extra_data = ui.item.data.split('#');\
            $('#id_part_description').val(extra_data[0]);\
            $('#id_supplier').val(extra_data[1]);\
            $('#id_location').val(extra_data[2]);\
            if (extra_data[3] != "0") {\
                $('#id_msds_form').val(extra_data[3])\
            } else {\
                $('#id_msds_form').val(null)\
            }\
            ;if (extra_data[4] != "") {\
                $('#id_price').val(extra_data[4])\
            } else {\
                $('#id_price').val(null)\
            }\
            ;if (extra_data[5] != "") {\
                $('#id_cas_number').val(extra_data[5])\
            } else {\
                $('#id_cas_number').val(null)\
            }\
            ;if (extra_data[6] != "") {\
                $('#id_ghs_pictogram').val(extra_data[6])\
            } else {\
                $('#id_ghs_pictogram').val(null)\
            }\
            ;\
        }\
    });\
    });"""
    
    # Write to file
    with open(BASE_DIR + "/static/admin/js/order_management/product-autocomplete.js","w") as out_handle_js:
        out_handle_js.write(jsmin(header_js + footer_js))

#################################################
#         CUSTOM MASS UPDATE FUNCTION           #
#################################################

def mass_update(modeladmin, request, queryset):
    """
        mass update queryset
        From adminactions.mass_update. Modified to allow specifiying a custom form
        and run update_autocomplete_js()
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

    # Allows to specify a custom mass update Form in ModelAdmin
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

    model = order_management_OrderExtraDoc
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
                    DJANGO_PRIVATE_DATA["server_email_address"],
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
    """Export all chemicals as xlsx. A chemical is defines as an order
    which has a non-null ghs_pictogram field and is not used up"""

    queryset = order_management_Order.objects.exclude(status="used up").annotate(text_len=Length('ghs_pictogram')).filter(text_len__gt=0).order_by('-id')
    export_data = OrderChemicalExportResource().export(queryset)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="Chemicals_{}_{}.xlsx'.format(time.strftime("%Y%m%d"), time.strftime("%H%M%S"))
    response.write(export_data.xlsx)
    return response
export_chemicals.short_description = "Export chemicals as xlsx"

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

    name = 'location'
    model = order_management_Location
    suggest_options = True

    def get_options(self):
        return order_management_Location.objects.all().order_by('name').\
        values_list('name', flat=True)

    def get_lookup_name(self):
        return 'location__name'

class SearchFieldOptCostUnit(StrField):
    """Create a list of unique cost units for search"""

    model = order_management_CostUnit
    name = 'cost_unit'
    suggest_options = True

    def get_options(self):
        return order_management_CostUnit.objects.all().order_by('name').\
        values_list('name', flat=True)

    def get_lookup_name(self):
        return 'cost_unit__name'

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

class SearchFieldOptUsernameOrder(SearchFieldOptUsername):
    """Create a list of unique users' usernames for search"""

    id_list = order_management_Order.objects.all().values_list('created_by', flat=True).distinct()

class SearchFieldOptLastnameOrder(SearchFieldOptLastname):
    """Create a list of unique users' usernames for search"""

    id_list = order_management_Order.objects.all().values_list('created_by', flat=True).distinct()

class OrderQLSchema(DjangoQLSchema):
    '''Customize search functionality'''
    
    include = (order_management_Order, User, order_management_CostUnit, order_management_Location) # Include only the relevant models to be searched

    suggest_options = {
        order_management_Order: ['status', 'supplier', 'urgent'],
    }

    def get_fields(self, model):
        ''' Define fields that can be searched'''
        
        if model == order_management_Order:
            return ['id', SearchFieldOptSupplier() ,'supplier_part_no', 'internal_order_no', SearchFieldOptPartDescription(), SearchFieldOptCostUnit(), 
            'status', 'urgent', SearchFieldOptLocation(), 'comment', 'delivered_date', 'cas_number', 
            'ghs_pictogram', 'created_date_time', 'last_changed_date_time', 'created_by',]
        elif model == User:
            return [SearchFieldOptUsernameOrder(), SearchFieldOptLastnameOrder()]
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
    actions = [change_order_status_to_arranged, change_order_status_to_delivered, change_order_status_to_used_up, export_orders, export_chemicals, mass_update]
    search_fields = ['id', 'part_description', 'supplier_part_no']
    
    def save_model(self, request, obj, form, change):
        
        if obj.pk == None:

            # New orders

            # If an order is new, assign the request user to it only if the order's created_by
            # attribute is not null

            try:
                obj.created_by
            except:
                obj.created_by = request.user
            try:
                
                # If a product name is not already present in the database,
                # update the automplete js file

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
            
            # Add approval record
            obj.approval.create(activity_type='created', activity_user=obj.history.latest().history_user)

            # Send email to Lab Managers if an order is set as urgent
            if obj.urgent:
                message = """Dear lab managers,

                {} {} has just placed an urgent order for {} {} - {}.

                Regards,
                The {}

                """.format(request.user.first_name, request.user.last_name, obj.supplier, obj.supplier_part_no, obj.part_description, SITE_TITLE)
                message = inspect.cleandoc(message)
                try:
                    send_mail('New urgent order', 
                    message, 
                    DJANGO_PRIVATE_DATA["server_email_address"],
                    DJANGO_PRIVATE_DATA["ordering_email_addresses"],
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
                order = order_management_Order.objects.get(pk=obj.pk)
                
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
                                        DJANGO_PRIVATE_DATA["server_email_address"],
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
            if not (request.user.groups.filter(name='Lab manager').exists() or request.user.groups.filter(name='Order manager').exists()):
                return ['supplier','supplier_part_no', 'internal_order_no', 'part_description', 'quantity', 
            'price', 'cost_unit', 'status', 'urgent', 'delivery_alert', 'location', 'comment', 'url', 'delivered_date', 'cas_number', 
            'ghs_pictogram', 'msds_form', 'order_manager_created_date_time', 'created_date_time', 'last_changed_date_time', 'created_by',]
            else:
                return ['urgent', 'delivery_alert', 'delivered_date', 'order_manager_created_date_time','created_date_time', 'last_changed_date_time',]
        else:
            return ['order_manager_created_date_time', 'created_date_time',  'last_changed_date_time',]

    def add_view(self, request, extra_context=None):
        
        # Specifies which fields should be shown in the add view

        if request.user.groups.filter(name='Lab manager').exists() or request.user.groups.filter(name='Order manager').exists():            
            self.fields = ('supplier','supplier_part_no', 'part_description', 'quantity', 
            'price', 'cost_unit', 'status', 'urgent', 'delivery_alert', 'location', 'comment', 'url', 'cas_number', 
            'ghs_pictogram', 'msds_form', 'created_by')
            self.raw_id_fields = []
            self.autocomplete_fields = []
            
        else:
            self.fields = ('supplier','supplier_part_no', 'part_description', 'quantity', 'price', 'cost_unit', 'urgent',
            'delivery_alert', 'location', 'comment', 'url', 'cas_number', 'ghs_pictogram', 'msds_form')
            self.raw_id_fields = ['msds_form']
            self.autocomplete_fields = []
        
        return super(OrderPage,self).add_view(request, extra_context=extra_context)

    def change_view(self, request, object_id, extra_context=None):
        
        # Specifies which fields should be shown in the change view
        
        self.raw_id_fields = []
        self.autocomplete_fields = ['msds_form']

        self.fields = ('supplier','supplier_part_no', 'internal_order_no', 'part_description', 'quantity', 
            'price', 'cost_unit', 'status', 'urgent', 'delivery_alert', 'location', 'comment', 'url', 'cas_number', 
            'ghs_pictogram', 'msds_form', 'created_date_time', 'order_manager_created_date_time', 'delivered_date', 'created_by',)
        return super(OrderPage,self).change_view(request, object_id, extra_context=extra_context)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        
        # Hide Save buttons when certain conditions (same as those in get_readonly_fields method) are met

        extra_context = extra_context or {}
        extra_context['show_submit_line'] = True
        if object_id:
            obj = order_management_Order.objects.get(pk=object_id)
            if obj:
                if not (request.user.groups.filter(name='Lab manager').exists() or request.user.groups.filter(name='Order manager').exists()):
                    extra_context['show_submit_line'] = False
        
        return super(OrderPage, self).changeform_view(request, object_id, form_url, extra_context=extra_context)
    
    def changelist_view(self, request, extra_context=None):
        
        # Set queryset of action export_chemicals to all orders

        if 'action' in request.POST and request.POST['action'] == 'export_chemicals':
            if not request.POST.getlist(admin.ACTION_CHECKBOX_NAME):
                post = request.POST.copy()
                for u in order_management_Order.objects.all():
                    post.update({admin.ACTION_CHECKBOX_NAME: str(u.id)})
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
            return mark_safe('<span style="width:100%; height:100%; background-color:#D5D8DC;">{}</span>'.format(instance.delivered_date.strftime('%d.%m.%Y') if instance.delivered_date else status.capitalize()))
        elif status == "cancelled":
            return mark_safe('<span style="width:100%; height:100%; background-color:#000000; color: white;">{}</span>'.format(status.capitalize()))
        elif status == "used up":
            return mark_safe('<span style="width:100%; height:100%; border-style: double;">{}</span>'.format(status.capitalize()))

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
            return mark_safe('<a href="{0}">View</a>'.format(instance.msds_form.name.url))
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

class MsdsFormForm(forms.ModelForm):
    def clean_name(self):
        
        # Check if the name of a MSDS form is unique before saving
        
        qs = order_management_MsdsForm.objects.filter(name__icontains=self.cleaned_data["name"].name)
        if qs:
            raise forms.ValidationError('A form with this name already exists.')
        else:
            return self.cleaned_data["name"]

class MsdsFormPage(DjangoQLSearchMixin, admin.ModelAdmin):
    
    list_display = ('id', 'pretty_file_name', 'view_file_link')
    list_per_page = 25
    ordering = ['name']
    djangoql_schema = MsdsFormQLSchema
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
        return(mark_safe("<a href='{}'>{}</a>".format(instance.name.url, "View")))
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

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
 
        # Hide Save buttons when certain conditions (same as those in get_readonly_fields method) are met
        extra_context = extra_context or {}
        extra_context['show_submit_line'] = True
        if object_id:
            extra_context['show_submit_line'] = False
        return super(OrderExtraDocPage, self).changeform_view(request, object_id, form_url, extra_context=extra_context)

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