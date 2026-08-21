"""Unfold admin registrations for providers and API endpoints."""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.widgets import UnfoldAdminTextInputWidget

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
        (_("Provider"), {"fields": ("name", "slug", "website", "is_active")}),
        (_("Description"), {"fields": ("description",)}),
        (_("Timestamps"), {"fields": ("created_at", "updated_at")}),
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
            _("Connection"),
            {"fields": ("provider", "name", "base_url", "api_key", "is_active")},
        ),
        (_("Description"), {"fields": ("description",)}),
        (_("Security"), {"fields": ("masked_api_key_display",)}),
        (_("Timestamps"), {"fields": ("created_at", "updated_at")}),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Users may submit a new key without being allowed to retrieve an
        # existing one. Hide the field only on change forms.
        if obj is not None and not request.user.has_perm("providers.view_sensitive_api_key"):
            form.base_fields.pop("api_key", None)
        elif obj is not None:
            form.base_fields["api_key"].widget = UnfoldAdminTextInputWidget()
            form.base_fields["api_key"].initial = obj.api_key
        return form

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj is None or request.user.has_perm("providers.view_sensitive_api_key"):
            return fieldsets
        return tuple((title, {**options, "fields": tuple(field for field in options.get("fields", ()) if field != "api_key")}) for title, options in fieldsets)

    @admin.display(description=_("API key"))
    def masked_api_key_display(self, obj: APIEndpoint) -> str:
        return obj.masked_api_key
