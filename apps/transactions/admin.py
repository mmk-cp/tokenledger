"""Unfold admin registration for the manual transaction ledger."""

from django.contrib import admin

from apps.core.admin import BaseModelAdmin
from apps.transactions.models import ExpenseCategory, Transaction


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(BaseModelAdmin):
    """Unfold administration for business expense categories."""

    list_display = ("name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Transaction)
class TransactionAdmin(BaseModelAdmin):
    """Unfold administration for manually recorded financial events."""

    list_display = (
        "transaction_type",
        "direction",
        "amount",
        "currency",
        "expense_category",
        "counterparty",
        "customer",
        "wallet",
        "transaction_date",
    )
    list_filter = (
        "transaction_type",
        "direction",
        "expense_category",
        "currency",
        "transaction_date",
    )
    search_fields = (
        "description",
        "reference",
        "counterparty",
        "external_reference",
        "expense_category__name",
        "customer__name",
        "customer__company_name",
    )
    ordering = ("-transaction_date", "-created_at")
    list_select_related = (
        "customer",
        "wallet",
        "credit_purchase",
        "allocation",
        "expense_category",
    )
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "Transaction Information",
            {
                "fields": (
                    "transaction_type",
                    "direction",
                    "expense_category",
                    "transaction_date",
                )
            },
        ),
        (
            "Related Objects",
            {"fields": ("customer", "wallet", "credit_purchase", "allocation")},
        ),
        (
            "Financial Details",
            {"fields": ("amount", "currency", "exchange_rate")},
        ),
        (
            "Metadata and Notes",
            {
                "fields": (
                    "counterparty",
                    "external_reference",
                    "reference",
                    "description",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
