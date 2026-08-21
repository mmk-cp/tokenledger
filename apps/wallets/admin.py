"""Unfold admin registration for cryptocurrency wallets."""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.core.admin import BaseModelAdmin
from apps.currencies.models import Currency
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
    search_fields = (
        "name",
        "currency__code",
        "currency__name",
        "network",
        "address",
        "description",
    )
    ordering = ("name",)
    list_select_related = ("currency",)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is None:
            form.base_fields["currency"].queryset = Currency.objects.filter(
                is_active=True
            ).order_by("code")
        return form
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            _("Wallet"),
            {"fields": ("name", "currency", "network", "address", "is_active")},
        ),
        (_("Description"), {"fields": ("description",)}),
        (_("Timestamps"), {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description=_("Address"), ordering="address")
    def masked_address_display(self, obj: Wallet) -> str:
        return obj.masked_address
