from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.forms import ValidationError

from approval.models import Approval
from common.models import DocFileMixin, HistoryFieldMixin, SaveWithoutHistoricalRecord

from ..ghssymbol.models import GhsSymbol
from ..hazardstatement.models import HazardStatement
from ..signalword.models import SignalWord


def validate_absence_airquotes(value):
    if "'" in value or '"' in value:
        raise ValidationError(
            "Single {} or double {} air-quotes are not allowed in this field".format(
                "'", '"'
            )
        )


User = get_user_model()

ORDER_STATUS_CHOICES = (
    ("submitted", "submitted"),
    ("open", "open"),
    ("arranged", "arranged"),
    ("delivered", "delivered"),
    ("cancelled", "cancelled"),
    ("used up", "used up"),
)

HAZARD_LEVEL_PREGNANCY_CHOICES = (
    ("none", "none"),
    ("yellow", "yellow"),
    ("red", "red"),
)


class Order(SaveWithoutHistoricalRecord, HistoryFieldMixin):
    _model_abbreviation = "order"
    _history_view_ignore_fields = [
        "created_approval_by_pi",
        "approval",
        "created_date_time",
        "last_changed_date_time",
    ]
    _history_array_fields = {
        "history_ghs_symbols": GhsSymbol,
        "history_signal_words": SignalWord,
        "history_hazard_statements": HazardStatement,
    }

    supplier = models.CharField(
        "supplier", max_length=255, blank=False, validators=[validate_absence_airquotes]
    )
    supplier_part_no = models.CharField(
        "supplier Part-No",
        max_length=255,
        blank=False,
        validators=[validate_absence_airquotes],
        help_text="To see suggestions, type three characters or more",
    )
    internal_order_no = models.CharField(
        "internal order number", max_length=255, blank=True
    )
    part_description = models.CharField(
        "part description",
        max_length=255,
        blank=False,
        validators=[validate_absence_airquotes],
        help_text="To see suggestions, type three characters or more",
    )
    quantity = models.CharField(
        "quantity", max_length=255, blank=False, validators=[validate_absence_airquotes]
    )
    price = models.CharField(
        "price", max_length=255, blank=True, validators=[validate_absence_airquotes]
    )
    cost_unit = models.ForeignKey(
        "CostUnit", on_delete=models.PROTECT, default=1, null=True, blank=False
    )
    status = models.CharField(
        "status",
        max_length=255,
        choices=ORDER_STATUS_CHOICES,
        default="submitted",
        blank=False,
    )
    urgent = models.BooleanField("is this an urgent order?", default=False)
    delivery_alert = models.BooleanField("delivery notification?", default=False)
    sent_email = models.BooleanField(default=False, null=True)
    location = models.ForeignKey(
        "Location", on_delete=models.PROTECT, null=True, blank=False
    )
    comment = models.TextField("comments", blank=True)
    order_manager_created_date_time = models.DateTimeField(
        "created in OrderManager", blank=True, null=True
    )
    delivered_date = models.DateField("delivered", blank=True, default=None, null=True)
    url = models.URLField("URL", max_length=400, blank=True)
    cas_number = models.CharField(
        "CAS number",
        max_length=255,
        blank=True,
        validators=[validate_absence_airquotes],
    )
    ghs_pictogram_old = models.CharField(
        "GHS pictogram",
        max_length=255,
        blank=True,
        validators=[validate_absence_airquotes],
    )
    ghs_symbols = models.ManyToManyField(
        "GhsSymbol",
        verbose_name="GHS symbols",
        related_name="order_ghs_symbols",
        blank=True,
    )
    hazard_statements = models.ManyToManyField(
        "HazardStatement",
        verbose_name="hazard statements",
        related_name="order_hazard_statement",
        blank=True,
    )
    signal_words = models.ManyToManyField(
        "SignalWord",
        verbose_name="signal words",
        related_name="order_signal_words",
        blank=True,
    )
    history_ghs_symbols = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="GHS symbols",
        blank=True,
        null=True,
        default=list,
    )
    history_signal_words = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="signal words",
        blank=True,
        null=True,
        default=list,
    )
    history_hazard_statements = ArrayField(
        models.PositiveIntegerField(),
        verbose_name="hazard statements",
        blank=True,
        null=True,
        default=list,
    )
    msds_form = models.ForeignKey(
        "MsdsForm",
        on_delete=models.PROTECT,
        verbose_name="MSDS form",
        blank=True,
        null=True,
    )
    hazard_level_pregnancy = models.CharField(
        "Hazard level for pregnancy",
        max_length=255,
        choices=HAZARD_LEVEL_PREGNANCY_CHOICES,
        default="none",
        blank=True,
    )

    created_date_time = models.DateTimeField("created", auto_now_add=True, null=True)
    last_changed_date_time = models.DateTimeField(
        "last changed", auto_now=True, null=True
    )
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    created_approval_by_pi = models.BooleanField(default=False, null=True)
    approval = GenericRelation(Approval)

    class Meta:
        verbose_name = "order"

    def __str__(self):
        return "{} - {}".format(self.id, self.part_description)

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        # Remove trailing whitespace and internal new-line characters from specific fields
        self.supplier = self.supplier.strip().replace("\n", " ")
        self.supplier_part_no = self.supplier_part_no.strip().replace("\n", " ")
        self.part_description = self.part_description.strip().replace("\n", " ")
        self.quantity = self.quantity.strip().replace("\n", " ")
        self.price = self.price.strip().replace("\n", " ")
        self.cas_number = self.cas_number.strip().replace("\n", " ")
        self.ghs_pictogram_old = self.ghs_pictogram_old.strip().replace("\n", " ")

        super().save(force_insert, force_update, using, update_fields)


#################################################
#             Order extra Doc model             #
#################################################


class OrderExtraDoc(DocFileMixin):
    comment = None
    description = models.CharField("description", max_length=255, blank=False)

    order = models.ForeignKey(Order, on_delete=models.PROTECT, null=True)

    class Meta:
        verbose_name = "order extra document"

    _mixin_props = {
        "destination_dir": "ordering/orderextradoc/",
        "file_prefix": "orderDoc",
        "parent_field_name": "order",
    }
