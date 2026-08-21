"""Unfold administration for manually maintained exchange rates."""

from django.contrib import admin

from apps.core.admin import BaseModelAdmin
from apps.currencies.models import ExchangeRate


@admin.register(ExchangeRate)
class ExchangeRateAdmin(BaseModelAdmin):
    """Unfold administration for historical exchange rates."""

    list_display = (
        "base_currency",
        "target_currency",
        "rate",
        "effective_date",
        "is_active",
    )
    list_filter = (
        "base_currency",
        "target_currency",
        "is_active",
        "effective_date",
    )
    search_fields = ("base_currency", "target_currency", "description")
    ordering = ("-effective_date", "base_currency", "target_currency")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "Exchange Rate",
            {"fields": ("base_currency", "target_currency", "rate")},
        ),
        ("Validity", {"fields": ("effective_date", "is_active")}),
        ("Notes", {"fields": ("description",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
