"""Unfold administration for manually maintained exchange rates."""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.core.admin import BaseModelAdmin
from apps.currencies.models import Currency, ExchangeRate


@admin.register(Currency)
class CurrencyAdmin(BaseModelAdmin):
    """Unfold administration for the dynamic currency catalog."""

    list_display = ("code", "name", "currency_type", "decimal_places", "is_active")
    list_filter = ("currency_type", "is_active")
    search_fields = ("code", "name")
    ordering = ("code",)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (_("Currency"), {"fields": ("code", "name", "symbol", "currency_type")}),
        (_("Configuration"), {"fields": ("decimal_places", "is_active")}),
        (_("Timestamps"), {"fields": ("created_at", "updated_at")}),
    )


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
    search_fields = (
        "base_currency__code",
        "base_currency__name",
        "target_currency__code",
        "target_currency__name",
        "description",
    )
    ordering = ("-effective_date", "base_currency__code", "target_currency__code")
    list_select_related = ("base_currency", "target_currency")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            _("Exchange Rate"),
            {"fields": ("base_currency", "target_currency", "rate")},
        ),
        (_("Validity"), {"fields": ("effective_date", "is_active")}),
        (_("Notes"), {"fields": ("description",)}),
        (_("Timestamps"), {"fields": ("created_at", "updated_at")}),
    )
