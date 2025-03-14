from functools import reduce

from django.contrib.auth import get_user_model
from django.db.models import Q
from djangoql.schema import StrField

User = get_user_model()


class SearchFieldWithOptions(StrField):
    """Search field with unlimited options"""

    suggest_options = True
    limit_options = None

    def get_options(self, search):
        filter_search = {f"{self.model_fieldname}__icontains": search}

        if self.limit_options:
            if len(search) < 3:
                return ["Type 3 or more characters to see suggestions"]
            return (
                self.model.objects.filter(**filter_search)
                .distinct()[: self.limit_options]
                .values_list(
                    self.name
                    if self.name == self.model_fieldname
                    else self.model_fieldname,
                    flat=True,
                )
            )

        return (
            self.model.objects.filter(**filter_search)
            .order_by(self.model_fieldname)
            .values_list(self.model_fieldname, flat=True)
        )

    def get_lookup_name(self):
        if self.name == self.model_fieldname:
            return self.name
        return f"{self.name}__{self.model_fieldname}"


class SearchFieldUserUsernameWithOptions(StrField):
    """Create a list of unique users' usernames for search"""

    model = User
    name = "username"
    suggest_options = True
    id_list = []

    def get_options(self, search):
        """Removes admin, guest and anonymous accounts from
        the list of options, distinct() returns only unique values
        sorted in alphabetical order"""

        # from https://stackoverflow.com/questions/14907525/
        excluded_users = ["AnonymousUser", "guest", "admin"]
        q_list = map(lambda n: Q(username__iexact=n), excluded_users)
        q_list = reduce(lambda a, b: a | b, q_list)

        if self.id_list:
            return (
                self.model.objects.filter(
                    id__in=self.id_list, username__icontains=search
                )
                .exclude(q_list)
                .distinct()
                .order_by(self.name)
                .values_list(self.name, flat=True)
            )
        else:
            return (
                self.model.objects.filter(username__icontains=search)
                .exclude(q_list)
                .distinct()
                .order_by(self.name)
                .values_list(self.name, flat=True)
            )


class SearchFieldUserLastnameWithOptions(StrField):
    """Create a list of unique user's last names for search"""

    model = User
    name = "last_name"
    suggest_options = True
    id_list = []

    def get_options(self, search):
        """Removes admin, guest and anonymous accounts from
        the list of options, distinct() returns only unique values
        sorted in alphabetical order"""

        # from https://stackoverflow.com/questions/14907525/
        excluded_users = ["", "admin", "guest"]
        q_list = map(lambda n: Q(last_name__iexact=n), excluded_users)
        q_list = reduce(lambda a, b: a | b, q_list)

        if self.id_list:
            return (
                self.model.objects.filter(
                    id__in=self.id_list, last_name__icontains=search
                )
                .exclude(q_list)
                .distinct()
                .order_by(self.name)
                .values_list(self.name, flat=True)
            )
        else:
            return (
                self.model.objects.filter(last_name__icontains=search)
                .exclude(q_list)
                .distinct()
                .order_by(self.name)
                .values_list(self.name, flat=True)
            )
