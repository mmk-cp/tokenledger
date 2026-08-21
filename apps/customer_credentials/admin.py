from django.contrib import admin

from apps.core.admin import BaseModelAdmin
from apps.customer_credentials.forms import CustomerCredentialAdminForm
from apps.customer_credentials.models import CustomerCredential


@admin.register(CustomerCredential)
class CustomerCredentialAdmin(BaseModelAdmin):
    form = CustomerCredentialAdminForm
    list_display = ("customer", "provider", "endpoint", "credit_allocation", "assigned_credit_usd", "selling_price_usd", "status", "expire_date")
    list_filter = ("provider", "status", "expire_date", "credit_allocation")
    search_fields = ("customer__name", "customer__company_name", "provider__name", "endpoint__name", "credit_allocation__customer__name")
    list_select_related = ("customer", "provider", "endpoint", "credit_allocation")
    readonly_fields = ("masked_api_key_display", "created_at", "updated_at")
    fieldsets = (
        ("Assignment", {"fields": ("customer", "provider", "endpoint", "credit_allocation", "status")} ),
        ("Credential", {"fields": ("encrypted_api_key", "masked_api_key_display")} ),
        ("Financial Information", {"fields": ("assigned_credit_usd", "cost_price_usd", "selling_price_usd")} ),
        ("Validity", {"fields": ("start_date", "expire_date")} ),
        ("Notes", {"fields": ("notes",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")} ),
    )

    @admin.display(description="API key")
    def masked_api_key_display(self, obj):
        return obj.masked_api_key
