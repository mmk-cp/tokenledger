"""Unfold admin registrations for credit purchases and balances."""

from datetime import timedelta

from django.contrib import admin
from django.db.models import F, Func, IntegerField, Value
from django.utils import timezone

from apps.core.admin import BaseModelAdmin
from apps.credits.models import (
    CreditBalance,
    CreditPurchase,
    CustomerCreditAllocation,
)


class ExpirationFilter(admin.SimpleListFilter):
    title = "Expiration"
    parameter_name = "expiration"

    def lookups(self, request, model_admin):
        return (
            ("active", "Active"),
            ("expiring", "Expiring soon (30 days)"),
            ("expired", "Expired"),
        )

    def queryset(self, request, queryset):
        today = timezone.localdate()
        if self.value() == "active":
            return queryset.filter(status=CustomerCreditAllocation.Status.ACTIVE)
        if self.value() == "expiring":
            return queryset.filter(
                status=CustomerCreditAllocation.Status.ACTIVE,
                expire_date__gte=today,
                expire_date__lte=today + timedelta(days=30),
            )
        if self.value() == "expired":
            return queryset.filter(expire_date__lt=today)
        return queryset


@admin.register(CreditPurchase)
class CreditPurchaseAdmin(BaseModelAdmin):
    """Unfold administration for owner credit purchases."""

    list_display = (
        "name",
        "provider",
        "credit_amount_usd",
        "paid_amount",
        "paid_currency",
        "status",
        "purchase_date",
        "expire_date",
    )
    list_filter = ("provider", "status", "paid_currency", "purchase_date")
    search_fields = ("name", "provider__name")
    ordering = ("-purchase_date", "-created_at")
    list_select_related = ("provider", "endpoint", "wallet")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "Purchase",
            {
                "fields": (
                    "name",
                    "provider",
                    "endpoint",
                    "wallet",
                    "status",
                )
            },
        ),
        (
            "Amounts",
            {
                "fields": (
                    "credit_amount_usd",
                    "paid_amount",
                    "paid_currency",
                    "exchange_rate",
                )
            },
        ),
        ("Dates", {"fields": ("purchase_date", "expire_date")}),
        ("Notes", {"fields": ("notes",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(CreditBalance)
class CreditBalanceAdmin(BaseModelAdmin):
    """Unfold administration for purchase credit inventory."""

    list_display = (
        "purchase",
        "total_credit_usd",
        "used_credit_usd",
        "remaining_credit_usd",
        "created_at",
    )
    search_fields = ("purchase__name", "purchase__provider__name")
    ordering = ("-created_at",)
    list_select_related = ("purchase", "purchase__provider")
    readonly_fields = (
        "total_credit_usd",
        "remaining_credit_usd",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        ("Purchase", {"fields": ("purchase",)}),
        (
            "Inventory",
            {
                "fields": (
                    "total_credit_usd",
                    "used_credit_usd",
                    "remaining_credit_usd",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(CustomerCreditAllocation)
class CustomerCreditAllocationAdmin(BaseModelAdmin):
    """Unfold administration for reseller credit assignments."""

    list_display = (
        "customer",
        "provider",
        "credit_purchase",
        "allocated_credit_usd",
        "remaining_credit_usd",
        "cost_price_usd",
        "selling_price_usd",
        "profit_usd",
        "expire_date",
        "days_until_expiration_display",
        "status",
    )
    list_filter = ("provider", ExpirationFilter, "expire_date")
    search_fields = ("customer__name", "customer__company_name", "provider__name")
    ordering = ("-start_date", "-created_at")
    list_select_related = ("customer", "provider", "credit_purchase")
    readonly_fields = (
        "provider",
        "remaining_credit_usd",
        "profit_usd_display",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        (
            "Customer Information",
            {"fields": ("customer", "status")},
        ),
        (
            "Credit Source",
            {"fields": ("credit_purchase", "provider")},
        ),
        (
            "Financial Information",
            {
                "fields": (
                    "allocated_credit_usd",
                    "cost_price_usd",
                    "selling_price_usd",
                    "remaining_credit_usd",
                    "profit_usd_display",
                )
            },
        ),
        ("Validity", {"fields": ("start_date", "expire_date")}),
        ("Notes", {"fields": ("notes",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Profit (USD)")
    def profit_usd_display(self, obj: CustomerCreditAllocation):
        return obj.profit_usd

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            admin_days_until_expiration=Func(
                F("expire_date"),
                Value(timezone.localdate()),
                function="DATEDIFF",
                output_field=IntegerField(),
            )
        )

    @admin.display(description="Days Until Expiration", ordering="admin_days_until_expiration")
    def days_until_expiration_display(self, obj: CustomerCreditAllocation):
        if obj.expire_date is None:
            return "-"
        return obj.admin_days_until_expiration
