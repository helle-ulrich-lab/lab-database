from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils.text import capfirst

from .models import Approval

User = get_user_model()


class ContentTypeFilter(admin.SimpleListFilter):
    title = "record type"

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "record_type"

    def lookups(self, request, model_admin):
        """Show only models for which records to be approved exist"""

        list_of_models = []
        for content_type_id in (
            Approval.objects.all()
            .values_list("content_type__id", "content_type__model")
            .distinct()
            .order_by("content_type__model")
            .values_list("content_type__id", flat=True)
        ):
            content_type_obj = ContentType.objects.get(id=content_type_id)
            list_of_models.append(
                (
                    str(content_type_id),
                    capfirst(content_type_obj.model_class()._meta.verbose_name),
                )
            )

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
    title = "activity type"

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "activity_type"

    def lookups(self, request, model_admin):
        """Show only models for which records to be approved exist"""

        choices = Approval._meta.get_field("activity_type").choices

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
    title = "activity user"

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "activity_user"

    def lookups(self, request, model_admin):
        """Show only models for which records to be approved exist"""

        user_ids = (
            Approval.objects.all().values_list("activity_user", flat=True).distinct()
        )
        users = User.objects.filter(id__in=user_ids).order_by("last_name")

        # Set template to dropdown menu rather than plan list if > 5 users
        if users.count() > 5:
            self.template = "admin/dropdown_filter.html"

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
    title = "message?"

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "message_exists"

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
    title = "message sent?"

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "message_sent"

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
