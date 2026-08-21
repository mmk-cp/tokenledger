"""Unfold admin registrations for credit purchases and balances."""

from django.contrib import admin

from apps.core.admin import BaseModelAdmin
from apps.credits.models import CreditBalance, CreditPurchase


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
