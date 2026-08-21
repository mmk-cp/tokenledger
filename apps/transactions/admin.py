"""Unfold admin registration for the manual transaction ledger."""

from django.contrib import admin

from apps.core.admin import BaseModelAdmin
from apps.transactions.models import Transaction


@admin.register(Transaction)
class TransactionAdmin(BaseModelAdmin):
    """Unfold administration for manually recorded financial events."""

    list_display = (
        "transaction_type",
        "direction",
        "amount",
        "currency",
        "customer",
        "wallet",
        "transaction_date",
    )
    list_filter = ("transaction_type", "direction", "currency", "transaction_date")
    search_fields = (
        "description",
        "reference",
        "customer__name",
        "customer__company_name",
    )
    ordering = ("-transaction_date", "-created_at")
    list_select_related = ("customer", "wallet", "credit_purchase", "allocation")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "Transaction Information",
            {"fields": ("transaction_type", "direction", "transaction_date")},
        ),
        (
            "Related Objects",
            {"fields": ("customer", "wallet", "credit_purchase", "allocation")},
        ),
        (
            "Financial Details",
            {"fields": ("amount", "currency", "exchange_rate")},
        ),
        ("Notes", {"fields": ("description", "reference")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
