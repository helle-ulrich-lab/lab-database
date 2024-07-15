from django.contrib import admin
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.contrib.auth.models import User
from django.core.mail import send_mail
import inspect
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.utils.text import capfirst

from ordering.models import Order
from .models import RecordToBeApproved
from django.contrib.contenttypes.models import ContentType

from django.conf import settings
SITE_TITLE = getattr(settings, 'SITE_TITLE', 'Lab DB')
SERVER_EMAIL_ADDRESS = getattr(settings, 'SERVER_EMAIL_ADDRESS', 'email@example.com')

from django.utils import timezone

def approve_records(modeladmin, request, queryset):
    """Approve records"""

    now_time = timezone.now()
    success_message = False
    warning_message = False
    
    # Collection records, except oligo
    collections_approval_records = queryset.filter(content_type__app_label='collection')

    for approval_record in collections_approval_records.exclude(content_type__model='oligo'):
        obj = approval_record.content_object
        if request.user.id in obj.formz_projects.all().values_list('project_leader__id', flat=True):
            model = obj._meta.model
            if approval_record.activity_type=='created':
                if obj.last_changed_approval_by_pi==False:
                    model.objects.filter(id=obj.id).update(created_approval_by_pi=True, last_changed_approval_by_pi=True, approval_by_pi_date_time=now_time, approval_user=request.user)
                else:
                    model.objects.filter(id=obj.id).update(created_approval_by_pi=True, approval_by_pi_date_time=now_time, approval_user=request.user)
            elif approval_record.activity_type=='changed':
                model.objects.filter(id=obj.id).update(last_changed_approval_by_pi=True, approval_by_pi_date_time=now_time, approval_user=request.user)
            approval_record.delete()
            success_message = True
        else:
            warning_message = True
    
    # Oligos
    oligo_approval_records = collections_approval_records.filter(content_type__model='oligo')
    if oligo_approval_records:
        if request.user.labuser.is_principal_investigator:
            model = oligo_approval_records[0].content_object._meta.model
            for oligo_approval_record in oligo_approval_records:
                obj = oligo_approval_record.content_object
                if oligo_approval_record.activity_type=='created':
                    if obj.last_changed_approval_by_pi==False:
                        model.objects.filter(id=obj.id).update(created_approval_by_pi=True, last_changed_approval_by_pi=True, approval_by_pi_date_time=now_time)
                    else:
                        model.objects.filter(id=obj.id).update(created_approval_by_pi=True, approval_by_pi_date_time=now_time)
                elif oligo_approval_record.activity_type=='changed':
                    model.objects.filter(id=obj.id).update(last_changed_approval_by_pi=True, approval_by_pi_date_time=now_time)
            oligo_approval_records.delete()
            success_message = True
        else:
            messages.error(request, 'You are not allowed to approve oligos')
    
    #Orders
    order_approval_records = queryset.filter(content_type__app_label='ordering')
    if order_approval_records:
        if request.user.labuser.is_principal_investigator:
            model = order_approval_records[0].content_object._meta.model
            order_ids = order_approval_records.values_list('object_id', flat=True)
            model.objects.filter(id__in=order_ids).update(created_approval_by_pi=True)
            order_approval_records.delete()
            success_message = True
        else:
            messages.error(request, 'You are not allowed to approve orders')
    
    if success_message:
        messages.success(request, 'The records have been approved')

    if warning_message:
        messages.warning(request, 'Some/all of the records you have selected were not approved because you are not listed as a project leader for them')

    return HttpResponseRedirect(".")
approve_records.short_description = "Approve records"

def notify_user_edits_required(modeladmin, request, queryset):
    """Notify a user that a collection record must be edited"""

    queryset = queryset.filter(content_type__app_label='collection')

    if queryset.filter(message=''):
        messages.error(request, 'Some of the records you have selected do not have a message. Please add a message to them, and try again')
        return HttpResponseRedirect(".")
    else:
        user_ids= set(queryset.values_list('activity_user', flat=True).distinct())
        now_time = timezone.now()
        for user_id in user_ids:
            user = User.objects.get(id=user_id)
            records = [(str(rec.content_type.name).capitalize(), str(rec.content_object), rec.message) for rec in queryset.filter(activity_user__id=user_id)]

            records_str = ''
            for rec in records:
                records_str = records_str + '\t'.join(rec).strip() + '\n'

            message = """Dear {},

            {} has flagged some of your records to be amended. See below.

            {}
            Regards,
            The {}
            """
            
            message = inspect.cleandoc(message).format(user.first_name,
                                                       f'{request.user.first_name} {request.user.last_name}',
                                                       records_str, SITE_TITLE)

            send_mail('Some records that you have created/changed need your attention',
                    message, 
                    SERVER_EMAIL_ADDRESS,
                    [user.email],
                    fail_silently=False,)
        messages.success(request, 'Users have been notified of required edits')
        queryset.update(message_date_time=now_time, edited=False)
        return HttpResponseRedirect(".")
notify_user_edits_required.short_description = "Notify users of required edits"

def approve_all_new_orders(modeladmin, request, queryset):
    """Approve all new orders """

    if request.user.labuser.is_principal_investigator:
        orders = Order.objects.filter(created_approval_by_pi=False)
        if orders.exists():
            orders.update(created_approval_by_pi=True)
            RecordToBeApproved.objects.filter(content_type__app_label='ordering').delete()
            messages.success(request, 'New orders have been approved')
        else:
            messages.warning(request, 'No new orders to approve')
    else:
        messages.error(request, 'You are not allowed to approve orders')

    return HttpResponseRedirect(".")

approve_all_new_orders.short_description = "Approve all new orders"

class ContentTypeFilter(admin.SimpleListFilter):

    title = 'record type'

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'record_type'

    def lookups(self, request, model_admin):
        """Show only models for which records to be approved exist"""
        
        list_of_models = []
        for content_type_id in RecordToBeApproved.objects.all().values_list('content_type__id', 'content_type__model').distinct().order_by('content_type__model').values_list('content_type__id', flat=True):
            content_type_obj = ContentType.objects.get(id=content_type_id)
            list_of_models.append((str(content_type_id), capfirst(content_type_obj.model_class()._meta.verbose_name)))

        return tuple(list_of_models)

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """

        if self.value():
            return queryset.filter(content_type=int(self.value()))
        else:
            return queryset

class ActivityTypeFilter(admin.SimpleListFilter):

    title = 'activity type'

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'activity_type'

    def lookups(self, request, model_admin):
        """Show only models for which records to be approved exist"""
        
        choices = RecordToBeApproved._meta.get_field('activity_type').choices

        return tuple((c1, capfirst(c2)) for c1, c2 in choices)

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """

        if self.value():
            return queryset.filter(activity_type=self.value())
        else:
            return queryset

class ActivityUserFilter(admin.SimpleListFilter):

    title = 'activity user'

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'activity_user'

    def lookups(self, request, model_admin):
        """Show only models for which records to be approved exist"""
        
        user_ids = RecordToBeApproved.objects.all().values_list("activity_user", flat=True).distinct()
        users = User.objects.filter(id__in=user_ids).order_by("last_name")

        # Set template to dropdown menu rather than plan list if > 5 users
        if users.count() > 5:
            self.template = 'admin/dropdown_filter.html'

        return tuple((u.id, u) for u in users)

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """

        if self.value():
            return queryset.filter(activity_user__id=self.value())
        else:
            return queryset

class MessageExistsFilter(admin.SimpleListFilter):

    title = 'message?'

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'message_exists'

    def lookups(self, request, model_admin):

        return (("1", "Yes"), ("0", "No"))

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """

        if self.value():
            if self.value() == "1":
                return queryset.exclude(message="")
            else:
                return queryset.filter(message="")
        else:
            return queryset

class MessageSentFilter(admin.SimpleListFilter):

    title = 'message sent?'

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'message_sent'

    def lookups(self, request, model_admin):

        return (("1", "Yes"), ("0", "No"))

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """

        if self.value():
            if self.value() == "1":
                return queryset.filter(message_date_time__isnull=False)
            else:
                return queryset.filter(message_date_time__isnull=True)
        else:
            return queryset

class RecordToBeApprovedPage(admin.ModelAdmin):
    
    list_display = ('magnificent_id', 'titled_content_type', 'record_link', 'coloured_activity_type', 'activity_user', 'history_link', 'message_exists', 'message_sent','edited', )
    list_display_links = None
    list_per_page = 50
    ordering = ['content_type', '-activity_type', 'object_id']
    actions = [approve_records, notify_user_edits_required, approve_all_new_orders]
    list_filter = (ContentTypeFilter, ActivityTypeFilter, ActivityUserFilter, MessageExistsFilter, MessageSentFilter, 'edited',)
    
    def get_readonly_fields(self, request, obj=None):
        
        # Specifies which fields should be shown as read-only and when
        
        if obj:
            return ['content_type', 'object_id', 'content_object', 'activity_type', 'activity_user',
                    'message_date_time', 'edited', 'created_date_time',]
        else:
            return ['created_date_time',]

    def changelist_view(self, request, extra_context=None):
        
        # Set queryset of action approve_all_new_orders

        if 'action' in request.POST and request.POST['action'] == 'approve_all_new_orders':
            if not request.POST.getlist(admin.helpers.ACTION_CHECKBOX_NAME):
                post = request.POST.copy()
                for u in Order.objects.all():
                    post.update({admin.helpers.ACTION_CHECKBOX_NAME: str(u.id)})
                request._set_post(post)
        return super(RecordToBeApprovedPage, self).changelist_view(request, extra_context=extra_context)

    def get_queryset(self, request):
        
        qs = super(RecordToBeApprovedPage, self).get_queryset(request)

        # If user is approval manager show only collection items, not orders

        if request.user.labuser.is_principal_investigator or request.user.is_superuser or request.user.groups.filter(name='Lab manager').exists():
            return qs
        elif request.user.groups.filter(name='Approval manager').exists():
            qs = qs.filter(content_type__app_label='collection').exclude(content_type__model='oligo')
            approval_record_ids = []
            for approval_record in qs:
                obj = approval_record.content_object
                if request.user.id in obj.formz_projects.all().values_list('project_leader__id', flat=True):
                    approval_record_ids.append(approval_record.id)
            return qs.filter(id__in=approval_record_ids)
        else:
            return qs

    def record_link(self, instance):
        '''Custom link to a record field for changelist_view'''

        url = reverse("admin:{}_{}_change".format(instance.content_object._meta.app_label, instance.content_object._meta.model_name), args=(instance.content_object.id,))
        record_name = str(instance.content_object)
        record_name =  record_name[:50] + "..." if len(record_name) > 50 else record_name 
       
        return mark_safe('<a class="magnific-popup-iframe-original-object" href="{}?_to_field=id&_popup=1&_approval=1" target="_blank">{}</a>'.format(url, record_name))

    record_link.short_description = 'Record'

    def history_link(self, instance):
        '''Custom link to a record's history field for changelist_view'''

        url = reverse("admin:{}_{}_history".format(instance.content_object._meta.app_label, instance.content_object._meta.model_name), args=(instance.content_object.id,))

        return mark_safe('<a class="magnific-popup-iframe-history" href="{}?_to_field=id&_popup=1" target="_blank">{}</a>'.format(url, 'History',))
    history_link.short_description = 'History'

    def titled_content_type(self, instance):
        '''Custom link to a record's history field for changelist_view'''

        return capfirst(instance.content_type.model_class()._meta.verbose_name)

    titled_content_type.short_description = 'Record type'
    titled_content_type.admin_order_field = 'content_type'

    def coloured_activity_type(self, instance):
        '''changew_view column to show created activity_type in red'''
        
        if instance.activity_type == 'created':
            return mark_safe('<span class="activity-created"">Created</span>')
        elif instance.activity_type == 'changed':
            return 'Changed'

    coloured_activity_type.short_description = 'Activity type'
    coloured_activity_type.admin_order_field = 'activity_type'

    def message_sent(self, instance):
        '''changew_view column to show whether a message has been sent or not'''

        if instance.message_date_time:
            return True
        else:
            return False
    message_sent.boolean = True
    message_sent.short_description = "Message sent?"

    def message_exists(self, instance):
        '''changew_view column to show whether a message exists'''

        return bool(instance.message)
    message_exists.boolean = True
    message_exists.short_description = "Message?"
    message_exists.admin_order_field = 'message'

    def magnificent_id(self, instance):
        '''changew_view column to show approval record link with for magnificent popup'''
        
        url = reverse(f'admin:{self.model._meta.app_label}_{self.model._meta.model_name}_change', args=(instance.id,) )
        return mark_safe(f'<a class="magnific-popup-iframe-id" href="{url}?_to_field=id&_popup=1" target="_blank">{instance.id}</a>')   
    magnificent_id.short_description = 'Approval ID'