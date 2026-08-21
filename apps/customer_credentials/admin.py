from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.widgets import UnfoldAdminPasswordWidget

from apps.core.admin import BaseModelAdmin
from apps.customer_credentials.forms import CustomerCredentialAdminForm
from apps.customer_credentials.models import CustomerCredential


@admin.register(CustomerCredential)
class CustomerCredentialAdmin(BaseModelAdmin):
    form = CustomerCredentialAdminForm
    list_display = ("customer", "provider", "endpoint", "credit_allocation", "assigned_credit_display", "cost_price_display", "selling_price_display", "status", "expire_date")
    list_filter = ("provider", "status", "expire_date", "credit_allocation")
    search_fields = ("customer__name", "customer__company_name", "provider__name", "endpoint__name", "credit_allocation__customer__name")
    list_select_related = ("customer", "provider", "endpoint", "credit_allocation")
    readonly_fields = ("masked_api_key_display", "allocation_financial_summary", "created_at", "updated_at")
    fieldsets = (
        (_("Assignment"), {"fields": ("customer", "provider", "endpoint", "credit_allocation", "status")} ),
        (_("Credential"), {"fields": ("api_key", "masked_api_key_display")} ),
        (_("Financial Information"), {"fields": ("allocation_financial_summary",)}),
        (_("Validity"), {"fields": ("start_date", "expire_date")} ),
        (_("Notes"), {"fields": ("notes",)}),
        (_("Timestamps"), {"fields": ("created_at", "updated_at")} ),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is not None and not request.user.has_perm("customer_credentials.view_sensitive_api_key"):
            form.base_fields.pop("api_key", None)
        elif obj is not None:
            form.base_fields["api_key"].widget = UnfoldAdminPasswordWidget(render_value=True)
        return form

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj is None or request.user.has_perm("customer_credentials.view_sensitive_api_key"):
            return fieldsets
        return tuple(
            (title, {**options, "fields": tuple(
                field for field in options.get("fields", ())
                if field != "api_key"
            )})
            for title, options in fieldsets
        )

    @admin.display(description=_("API key"))
    def masked_api_key_display(self, obj):
        return obj.masked_api_key

    def _allocation_value(self, obj, field):
        allocation = getattr(obj, "credit_allocation", None)
        return getattr(allocation, field, "-") if allocation else "-"

    @admin.display(description=_("Assigned credit USD"))
    def assigned_credit_display(self, obj):
        return self._allocation_value(obj, "allocated_credit_usd")

    @admin.display(description=_("Cost price USD"))
    def cost_price_display(self, obj):
        return self._allocation_value(obj, "cost_price_usd")

    @admin.display(description=_("Selling price USD"))
    def selling_price_display(self, obj):
        return self._allocation_value(obj, "selling_price_usd")

    @admin.display(description=_("Allocation financial summary"))
    def allocation_financial_summary(self, obj):
        allocation = getattr(obj, "credit_allocation", None)
        if not allocation:
            return _("No credit allocation linked.")
        return _(
            "Allocated: %(allocated)s USD | Cost: %(cost)s USD | Selling: %(selling)s USD"
        ) % {
            "allocated": f"{allocation.allocated_credit_usd:.2f}",
            "cost": f"{allocation.cost_price_usd or 0:.2f}",
            "selling": f"{allocation.selling_price_usd:.2f}",
        }
