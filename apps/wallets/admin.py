"""Unfold admin registration for cryptocurrency wallets."""

from django.contrib import admin

from apps.core.admin import BaseModelAdmin
from apps.wallets.models import Wallet


@admin.register(Wallet)
class WalletAdmin(BaseModelAdmin):
    """Unfold administration for operator-controlled wallets."""

    list_display = (
        "name",
        "currency",
        "network",
        "masked_address_display",
        "is_active",
        "created_at",
    )
    list_filter = ("currency", "network", "is_active")
    search_fields = ("name", "currency", "network", "address", "description")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "Wallet",
            {"fields": ("name", "currency", "network", "address", "is_active")},
        ),
        ("Description", {"fields": ("description",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Address", ordering="address")
    def masked_address_display(self, obj: Wallet) -> str:
        return obj.masked_address
