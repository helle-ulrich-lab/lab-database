from django.contrib import admin
from django.utils import timezone

from ..models import Order


class CostUnitAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "status", "expense")
    list_display_links = ("name",)
    list_per_page = 25
    ordering = ["name"]

    @admin.display(description="Yearly expense")
    def expense(self, instance):
        """
        Calculate the sum of money spent on a CostUnit within the current year
        """

        # Cast price to float if possible
        cast_price_sql_exp = r"""
                              CAST(
                                    (REGEXP_MATCH(REPLACE(price, ',', '.'), '\d*\.*\d+'))[1] AS FLOAT
                              )
                              """
        # Cast quantity to int by matching start of field
        # If string is empty, then return 1
        cast_quantity_sql_exp = r"""
                                 CAST(
                                     (COALESCE(
                                     (REGEXP_MATCH(quantity, '^\d+'))[1], '1')) AS INTEGER)
                                 """

        sum_prices = "-"
        if not instance.status:
            try:
                now = timezone.now()
                orders = (
                    Order.objects.filter(
                        cost_unit=instance, created_date_time__year=now.year
                    )
                    .exclude(price="")
                    .extra(
                        select={
                            "price_value": cast_price_sql_exp,
                            "quantity_value": cast_quantity_sql_exp,
                        }
                    )
                )

                sum_prices = sum(
                    p * q
                    for (p, q) in orders.values_list("price_value", "quantity_value")
                    if p
                )
                sum_prices = f"{round(sum_prices):,}"

            except Exception:
                sum_prices = "Error"

        return sum_prices
