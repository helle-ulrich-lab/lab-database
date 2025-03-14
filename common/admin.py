import itertools

from django.contrib import admin
from django.contrib.admin.utils import unquote
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.urls import path, resolve
from django.utils.encoding import force_str
from django.utils.safestring import mark_safe
from django.utils.text import capfirst
from django.utils.translation import gettext_lazy as _
from simple_history.admin import SimpleHistoryAdmin

User = get_user_model()


class OwnUserAdmin(BaseUserAdmin):
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_active",
        "get_user_groups",
    )
    critical_groups = None

    def save_model(self, request, obj, form, change):
        # Set is_active and is_staff to True for newly created users
        if obj.pk is None:
            obj.save()
            # Create User first, this triggers signal that sets is_active to false by default
            # therefore set is_active to True after creating the object
            obj.is_active = True
            obj.save()
        else:
            # If somebody tries to save a user for which it cannot see some of its groups,
            # save these groups to critical_groups and add them back to the user in save_related
            if request.user.is_superuser or request.user.is_pi:
                self.critical_groups = []
            else:
                old_user = User.objects.get(id=obj.pk)
                critical_groups = old_user.groups.exclude(
                    name__in=[
                        "Guest",
                        "Regular lab member",
                        "Order manager",
                        "Lab manager",
                        "Past member",
                    ]
                )
                self.critical_groups = list(critical_groups)

            obj.save()

        # If is_pi is True check whether a principal_investigator already exists
        # and if so set the field to False
        if obj.is_pi:
            if User.objects.filter(is_pi=True).exists():
                obj.is_pi = False
                obj.save()

    def save_related(self, request, form, formsets, change):
        """If somebody tries to save a user for which it cannot see some of its groups,
        get these groups from critical_groups and add them back to the user"""

        super().save_related(request, form, formsets, change)

        if self.critical_groups:
            obj = User.objects.get(pk=form.instance.id)
            for g in self.critical_groups:
                obj.groups.add(g)

    def get_readonly_fields(self, request, obj=None):
        """Override default get_readonly_fields to define user-specific read-only fields"""

        if obj:
            if request.user.is_superuser or request.user.is_pi:
                return ["oidc_id"]
            else:
                if obj.is_superuser or obj.is_pi:
                    return [
                        "groups",
                        "user_permissions",
                        "is_active",
                        "username",
                        "password",
                        "first_name",
                        "last_name",
                        "email",
                        "is_superuser",
                        "username",
                        "is_pi",
                        "oidc_id",
                    ]
                else:
                    return []
        else:
            return []

    def change_view(self, request, object_id, extra_context=None):
        """Override default change_view to show only desired fields"""

        extra_context = extra_context or {}

        if request.user.is_superuser:
            self.fieldsets = (
                (None, {"fields": ("username", "password")}),
                (
                    _("Personal info"),
                    {"fields": ("first_name", "last_name", "email", "oidc_id")},
                ),
                (
                    _("Permissions"),
                    {
                        "fields": (
                            "is_active",
                            "is_superuser",
                            "is_pi",
                            "groups",
                            "user_permissions",
                        ),
                    },
                ),
            )
        elif request.user.is_pi:
            self.fieldsets = (
                (None, {"fields": ("username", "password")}),
                (
                    _("Personal info"),
                    {
                        "fields": (
                            "first_name",
                            "last_name",
                            "email",
                        )
                    },
                ),
                (
                    _("Permissions"),
                    {
                        "fields": (
                            "is_active",
                            "is_pi",
                            "groups",
                        ),
                    },
                ),
            )
        elif request.user.has_perm("common.change_user"):
            obj = self.model.objects.get(id=object_id)
            user_fields = (
                ("username", "password") if obj.has_usable_password() else ("username",)
            )
            self.fieldsets = (
                (None, {"fields": user_fields}),
                (
                    _("Personal info"),
                    {
                        "fields": (
                            "first_name",
                            "last_name",
                            "email",
                        )
                    },
                ),
                (
                    _("Permissions"),
                    {
                        "fields": (
                            "is_active",
                            "is_pi",
                            "groups",
                        ),
                    },
                ),
            )
        else:
            self.fieldsets = (
                (None, {"fields": ("username",)}),
                (
                    _("Personal info"),
                    {
                        "fields": (
                            "first_name",
                            "last_name",
                            "email",
                        )
                    },
                ),
                (
                    _("Permissions"),
                    {
                        "fields": (
                            "is_active",
                            "is_pi",
                            "groups",
                        ),
                    },
                ),
            )

        return super().change_view(request, object_id, extra_context=extra_context)

    def get_formsets_with_inlines(self, request, obj=None):
        """Show is_pi inline only for superusers"""

        if request.user.is_superuser and obj:
            for inline in self.get_inline_instances(request, obj):
                yield inline.get_formset(request, obj), inline

    def get_queryset(self, request):
        # Show superusers only for superusers
        # Also do not show AnonymousUser

        qs = super().get_queryset(request)

        if not request.user.is_superuser:
            return qs.exclude(is_superuser=True).exclude(username="AnonymousUser")
        else:
            return qs.exclude(username="AnonymousUser")

    @admin.display(description="Groups")
    def get_user_groups(self, instance):
        """Pass a user's group membership to a custom column"""

        return ", ".join(instance.groups.values_list("name", flat=True))

    def user_pretty_name(self):
        """Create a pretty name for a user to be shown as its unicode attribute"""

        if self.first_name:
            pretty_name = self.first_name[0].upper() + ". " + self.last_name.title()
            return pretty_name
        else:
            return self.username

    User.__str__ = user_pretty_name

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """Show important groups only to superusers and principal investigators"""

        from django.contrib.auth.models import Group

        if db_field.name == "groups":
            if request.user.is_superuser or request.user.is_pi:
                kwargs["queryset"] = Group.objects.all()
            else:
                kwargs["queryset"] = Group.objects.filter(
                    name__in=[
                        "Guest",
                        "Regular lab member",
                        "Order manager",
                        "Lab manager",
                        "Past member",
                    ]
                )
        return super().formfield_for_manytomany(db_field, request, **kwargs)


class SimpleHistoryWithSummaryAdmin(SimpleHistoryAdmin):
    object_history_template = "admin/object_history_with_change_summary.html"
    history_array_fields = {}

    def history_view(self, request, object_id, extra_context=None):
        """The 'history' admin view for this model."""

        def pairwise(iterable):
            """Create pairs of consecutive items from
            iterable"""

            a, b = itertools.tee(iterable)
            next(b, None)
            return zip(a, b)

        request.current_app = self.admin_site.name
        model = self.model
        opts = model._meta
        app_label = opts.app_label
        pk_name = opts.pk.attname
        history = getattr(model, model._meta.simple_history_manager_attribute)
        object_id = unquote(object_id)
        action_list = history.filter(**{pk_name: object_id})

        # If no history was found, see whether this object even exists
        try:
            obj = self.get_queryset(request).get(**{pk_name: object_id})
        except model.DoesNotExist:
            try:
                obj = action_list.latest("history_date").instance
            except action_list.model.DoesNotExist:
                raise Http404

        context = self.admin_site.each_context(request)
        context.update(
            {
                "title": _("Change history: %s") % force_str(obj),
                "action_list": action_list,
                "module_name": capfirst(force_str(opts.verbose_name_plural)),
                "object": obj,
                "root_path": getattr(self.admin_site, "root_path", None),
                "app_label": app_label,
                "opts": opts,
                "is_popup": "_popup" in request.GET,
            }
        )
        context.update(extra_context or {})
        extra_kwargs = {}

        return render(request, self.object_history_template, context, **extra_kwargs)


class AdminChangeFormWithNavigation(admin.ModelAdmin):
    def get_urls(self):
        """
        Add navigation url
        """

        urls = super().get_urls()

        urls = [path("<path:object_id>/navigation/", view=self.navigation)] + urls

        return urls

    def navigation(self, request, *args, **kwargs):
        """Return previous or next record, if available"""

        direction = request.GET.get("direction", None)
        obj_redirect_id = None
        if direction:
            obj_id = int(kwargs["object_id"])
            try:
                if direction.endswith("next"):
                    obj_redirect_id = (
                        self.model.objects.filter(id__gt=obj_id)
                        .order_by("id")
                        .first()
                        .id
                    )
                else:
                    obj_redirect_id = (
                        self.model.objects.filter(id__lt=obj_id)
                        .order_by("-id")
                        .first()
                        .id
                    )
            except Exception:
                pass

        return JsonResponse({"id": obj_redirect_id})


class DocFileInlineMixin(admin.TabularInline):
    """Inline to view existing documents"""

    verbose_name_plural = "Existing docs"
    extra = 0
    fields = ["description", "get_doc_short_name", "comment", "created_date_time"]
    readonly_fields = [
        "description",
        "get_doc_short_name",
        "comment",
        "created_date_time",
    ]

    def get_parent_object(self, request):
        """
        Returns the parent object from the request or None.

        Note that this only works for Inlines, because the `parent_model`
        is not available in the regular admin.ModelAdmin as an attribute.
        """

        resolved = resolve(request.path_info)
        if resolved.kwargs:
            return self.parent_model.objects.get(pk=resolved.kwargs["object_id"])
        return None

    def get_queryset(self, request):
        """Show inline uncollapsed only if docs exist"""
        self.classes = [
            "collapse",
        ]

        qs = super().get_queryset(request)
        parent_object = self.get_parent_object(request)
        if parent_object:
            filter_params = {
                f"{self.model._mixin_props.get('parent_field_name')}__pk": parent_object.pk
            }
            if qs.filter(**filter_params).exists():
                self.classes = []
        return qs

    def has_add_permission(self, request, obj):
        return False

    @admin.display(description="Document")
    def get_doc_short_name(self, instance):
        if instance.name and instance.name.name.endswith("pdf"):
            return mark_safe(
                f'<a class="magnific-popup-iframe-pdflink" href="{instance.name.url}">View PDF</a>'
            )
        return mark_safe(f'<a href="{instance.name.url}">Download</a>')


class AddDocFileInlineMixin(admin.TabularInline):
    """Inline to add new documents"""

    verbose_name_plural = "New docs"
    extra = 0
    fields = ["description", "name", "comment"]

    def get_parent_object(self, request):
        """
        Returns the parent object from the request or None.

        Note that this only works for Inlines, because the `parent_model`
        is not available in the regular admin.ModelAdmin as an attribute.
        """

        resolved = resolve(request.path_info)
        if resolved.kwargs:
            return self.parent_model.objects.get(pk=resolved.kwargs["object_id"])
        return None

    def get_queryset(self, request):
        """show inline uncollpased only when adding a new record,
        also return an empty qs"""

        self.classes = [
            "collapse",
        ]

        parent_object = self.get_parent_object(request)
        if not parent_object:
            self.classes = []
        return self.model.objects.none()

    def has_change_permission(self, request, obj=None):
        return False


class ToggleDocInlineMixin(admin.ModelAdmin):
    def get_inline_instances(self, request, obj=None):
        inline_instances = super().get_inline_instances(request, obj)
        filtered_inline_instances = []

        # New objects
        if not obj:
            filtered_inline_instances = [
                i for i in inline_instances if i.verbose_name_plural != "Existing docs"
            ]

        # Existing objects
        else:
            for inline in inline_instances:
                # Always show existing docs
                if inline.verbose_name_plural == "Existing docs":
                    filtered_inline_instances.append(inline)
                else:
                    # Do not allow guests to add docs, ever
                    if not request.user.groups.filter(name="Guest").exists():
                        filtered_inline_instances.append(inline)

        return filtered_inline_instances

    # def get_formsets_with_inlines(self, request, obj=None):
    #     """Remove DocInline from add/change form if user who
    #     created a  object is not the request user a lab manager
    #     or a superuser"""

    #     # New objects
    #     if not obj:
    #         for inline in self.get_inline_instances(request, obj):
    #             # Do not show DocFileInlineMixin for new objetcs
    #             if inline.verbose_name_plural == 'Existing docs':
    #                 continue
    #             else:
    #                 yield inline.get_formset(request, obj), inline

    #     # Existing objects
    #     else:
    #         for inline in self.get_inline_instances(request, obj):
    #             # Always show existing docs
    #             if inline.verbose_name_plural == 'Existing docs':
    #                 yield inline.get_formset(request, obj), inline
    #             else:
    #                 # Do not allow guests to add docs, ever
    #                 if not request.user.groups.filter(name='Guest').exists():
    #                     yield inline.get_formset(request, obj), inline


def save_history_fields(obj, history_obj):
    history_array_fields = obj._history_array_fields.copy()
    m2m_save_ignore_fields = getattr(obj, "_m2m_save_ignore_fields", [])
    if m2m_save_ignore_fields:
        history_array_fields = {
            k: v
            for k, v in history_array_fields.items()
            if k not in m2m_save_ignore_fields
        }

    # Keep a record of the IDs of linked M2M fields in the main obj record
    # Not pretty, but it works

    for m2m_history_field_name, m2m_model in history_array_fields.items():
        try:
            m2m_set = getattr(obj, f"{m2m_history_field_name[8:]}")
        except Exception:
            try:
                m2m_set = getattr(obj, f"{m2m_model._meta.model_name}_set")
            except Exception:
                continue
        setattr(
            obj,
            m2m_history_field_name,
            (
                list(m2m_set.order_by("id").distinct("id").values_list("id", flat=True))
                if m2m_set.exists()
                else []
            ),
        )

    obj.save_without_historical_record()

    if history_obj:
        for (
            m2m_history_field_name,
            m2m_model,
        ) in obj._history_array_fields.items():
            setattr(
                history_obj,
                m2m_history_field_name,
                getattr(obj, m2m_history_field_name),
            )

        history_obj.save()
