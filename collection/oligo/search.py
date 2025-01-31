from django.contrib import messages
from django.contrib.auth.models import User
from django.core.exceptions import FieldError, ValidationError
from django.db import DataError, models
from django.db.models.functions import Collate
from djangoql.admin import DjangoQLSearchMixin
from djangoql.exceptions import DjangoQLError
from djangoql.parser import DjangoQLParser
from djangoql.queryset import build_filter
from djangoql.schema import DjangoQLSchema, StrField

from common.search import (
    SearchFieldUserLastnameWithOptions,
    SearchFieldUserUsernameWithOptions,
)

from ..shared.admin import (
    FieldCreated,
    FieldLastChanged,
    FieldUse,
)
from .models import Oligo


class OligoSearchFieldUserUsername(SearchFieldUserUsernameWithOptions):
    id_list = Oligo.objects.all().values_list("created_by", flat=True).distinct()


class OligoSearchFieldUserLastname(SearchFieldUserLastnameWithOptions):
    id_list = Oligo.objects.all().values_list("created_by", flat=True).distinct()


class OligoSearchFieldSequence(StrField):
    name = "sequence"

    def get_lookup(self, path, operator, value):
        """Override parent's method to include deterministic
        collation flag to lookup for sequence"""

        search = "__".join(path + [self.get_lookup_name()])
        search = (
            search.replace("sequence", "sequence_deterministic")
            if "sequence" in search
            else search
        )
        op, invert = self.get_operator(operator)
        q = models.Q(**{f"{search}{op}": self.get_lookup_value(value)})
        return ~q if invert else q


class OligoQLSchema(DjangoQLSchema):
    """Customize search functionality"""

    include = (Oligo, User)

    def get_fields(self, model):
        """Define fields that can be searched"""

        if model == Oligo:
            return [
                "id",
                "name",
                OligoSearchFieldSequence(),
                "length",
                FieldUse(),
                "gene",
                "restriction_site",
                "description",
                "comment",
                "created_by",
                FieldCreated(),
                FieldLastChanged(),
            ]
        elif model == User:
            return [OligoSearchFieldUserUsername(), OligoSearchFieldUserLastname()]
        return super().get_fields(model)


class OligoDjangoQLSearchMixin(DjangoQLSearchMixin):
    def get_search_results(self, request, queryset, search_term):
        """
        Filter sequence using a non-deterministic collaction
        """

        def apply_search(queryset, search, schema=None):
            ast = DjangoQLParser().parse(search)
            schema = schema or DjangoQLSchema
            schema_instance = schema(queryset.model)
            schema_instance.validate(ast)
            filter_params = build_filter(ast, schema_instance)
            if any(n[0].startswith("sequence") for n in filter_params.deconstruct()[1]):
                return queryset.annotate(
                    sequence_deterministic=Collate("sequence", "und-x-icu")
                ).filter(filter_params)
            return queryset.filter(filter_params)

        if self.search_mode_toggle_enabled() and not self.djangoql_search_enabled(
            request
        ):
            return super(DjangoQLSearchMixin, self).get_search_results(
                request=request,
                queryset=queryset,
                search_term=search_term,
            )
        use_distinct = False
        if not search_term:
            return queryset, use_distinct

        try:
            qs = apply_search(queryset, search_term, self.djangoql_schema)
        except (DjangoQLError, ValueError, FieldError, ValidationError) as e:
            msg = self.djangoql_error_message(e)
            messages.add_message(request, messages.WARNING, msg)
            qs = queryset.none()
        else:
            # Hack to handle 'inet' comparison errors in Postgres. If you
            # know a better way to check for such an error, please submit a PR.
            try:
                # Django >= 2.1 has built-in .explain() method
                explain = getattr(qs, "explain", None)
                if callable(explain):
                    explain()
                else:
                    list(qs[:1])
            except DataError as e:
                if "inet" not in str(e):
                    raise
                msg = self.djangoql_error_message(e)
                messages.add_message(request, messages.WARNING, msg)
                qs = queryset.none()

        return qs, use_distinct
