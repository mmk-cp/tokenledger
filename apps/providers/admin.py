"""Unfold admin registrations for providers and API endpoints."""

from django.contrib import admin

from apps.core.admin import BaseModelAdmin
from apps.providers.forms import APIEndpointAdminForm
from apps.providers.models import APIEndpoint, Provider


@admin.register(Provider)
class ProviderAdmin(BaseModelAdmin):
    """Unfold administration for AI service providers."""

    list_display = ("name", "slug", "website", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug", "description")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Provider", {"fields": ("name", "slug", "website", "is_active")}),
        ("Description", {"fields": ("description",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(APIEndpoint)
class APIEndpointAdmin(BaseModelAdmin):
    """Unfold administration for encrypted upstream API connections."""

    form = APIEndpointAdminForm
    list_display = (
        "name",
        "provider",
        "base_url",
        "masked_api_key_display",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "provider")
    search_fields = ("name", "base_url", "description", "provider__name")
    ordering = ("provider__name", "name")
    list_select_related = ("provider",)
    readonly_fields = ("masked_api_key_display", "created_at", "updated_at")
    fieldsets = (
        (
            "Connection",
            {"fields": ("provider", "name", "base_url", "api_key", "is_active")},
        ),
        ("Description", {"fields": ("description",)}),
        ("Security", {"fields": ("masked_api_key_display",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="API key")
    def masked_api_key_display(self, obj: APIEndpoint) -> str:
        return obj.masked_api_key
