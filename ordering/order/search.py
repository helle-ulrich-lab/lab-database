from django.contrib.auth.models import User
from djangoql.schema import BoolField, DjangoQLSchema, StrField

from common.search import (
    SearchCustomFieldUserLastnameWithOptions,
    SearchCustomFieldUserUsernameWithOptions,
    SearchCustomFieldWithOptions,
)

from ..models import (
    CostUnit,
    GhsSymbol,
    HazardStatement,
    Location,
    MsdsForm,
    Order,
    SignalWord,
)


class SearchFieldOrderLocation(SearchCustomFieldWithOptions):
    """Search an Order's Location with suggestions"""

    name = "location"
    model = Location
    model_fieldname = "name"


class SearchFieldOrderCostUnit(SearchCustomFieldWithOptions):
    """Search an Order's CostUnit with suggestions"""

    name = "cost_unit"
    model = CostUnit
    model_fieldname = "name"


class SearchFieldOrderSupplier(SearchCustomFieldWithOptions):
    """Search an Order's Supplier with suggestions"""

    name = "supplier"
    model = Order
    model_fieldname = name
    limit_options = 10


class SearchFieldOrderPartDescription(SearchCustomFieldWithOptions):
    """Search an Order's PartDescription with suggestions"""

    name = "part_description"
    model = Order
    model_fieldname = name
    limit_options = 10


class SearchFieldOrderHazardousPregnancy(StrField):
    """Search an Order's Hazardous for Pregnancy with suggestions"""

    model = Order
    name = "hazard_level_pregnancy"
    suggest_options = True


class SearchFieldOrderCreatedbyUsername(SearchCustomFieldUserUsernameWithOptions):
    """Search an Order's users' usernames"""

    id_list = Order.objects.all().values_list("created_by", flat=True).distinct()


class SearchFieldOrderCreatedbyLastname(SearchCustomFieldUserLastnameWithOptions):
    """Search an Order's users' last names"""

    id_list = Order.objects.all().values_list("created_by", flat=True).distinct()


class SearchFieldOrderGhsSymbol(SearchCustomFieldWithOptions):
    """Search an Order's GHS symbols with suggestions"""

    model = GhsSymbol
    name = "ghs_symbols"
    model_fieldname = "code"


class SearchFieldOrderSignalWord(SearchCustomFieldWithOptions):
    """Search an Order's Signal word with suggestions"""

    name = "signal_words"
    model = SignalWord
    model_fieldname = "signal_word"


class SearchFieldOrderMsdsForm(SearchCustomFieldWithOptions):
    """Search an Order's MSDS form with suggestions"""

    name = "msds_form"
    model = MsdsForm
    model_fieldname = "label"
    limit_options = 10


class SearchFieldOrderHasGhsSymbol(BoolField):
    """Search an Order for whether it has a GHS symbol"""

    model = Order
    name = "has_ghs_symbol"

    def get_lookup_name(self):
        return "ghs_symbols__code__isnull"

    def get_operator(self, operator):
        op, _ = super().get_operator(operator)
        return op, True


class SearchFieldOrderHazardSatetement(SearchCustomFieldWithOptions):
    """Search an Order's Hazard statements with suggestions"""

    name = "hazard_statements"
    model = HazardStatement
    model_fieldname = "code"


class SearchFieldOrderIsCmr(BoolField):
    """Search an Order for whether is CMR"""

    model = Order
    name = "is_cmr"

    def get_lookup_name(self):
        return "hazard_statements__is_cmr"


class OrderQLSchema(DjangoQLSchema):
    """Customize search functionality"""

    include = (
        Order,
        User,
        CostUnit,
        Location,
    )

    suggest_options = {
        Order: ["status", "supplier", "urgent"],
    }

    def get_fields(self, model):
        """Define fields that can be searched"""

        if model == Order:
            return [
                "id",
                SearchFieldOrderSupplier(),
                "supplier_part_no",
                "internal_order_no",
                SearchFieldOrderPartDescription(),
                SearchFieldOrderCostUnit(),
                "status",
                "urgent",
                SearchFieldOrderLocation(),
                "comment",
                "delivered_date",
                "cas_number",
                SearchFieldOrderGhsSymbol(),
                SearchFieldOrderHasGhsSymbol(),
                SearchFieldOrderSignalWord(),
                SearchFieldOrderMsdsForm(),
                SearchFieldOrderHazardSatetement(),
                SearchFieldOrderIsCmr(),
                SearchFieldOrderHazardousPregnancy(),
                "created_date_time",
                "last_changed_date_time",
                "created_by",
            ]
        elif model == User:
            return [
                SearchFieldOrderCreatedbyUsername(),
                SearchFieldOrderCreatedbyLastname(),
            ]
        return super().get_fields(model)
