"""Shared Unfold admin helpers and dashboard context."""

from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.db.models import Sum
from django.http import HttpRequest
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm

from apps.core.forms import UserChangeForm, UserCreationForm
from apps.core.models import AuditLog, User
from apps.credits.models import CustomerCreditAllocation, CreditPurchase
from apps.customers.models import Customer
from apps.transactions.models import Transaction


class BaseModelAdmin(ModelAdmin):
    """Base class for all TokenLedger model administration classes."""

    list_per_page = 50
    save_on_top = True
    warn_unsaved_form = True


if admin.site.is_registered(Group):
    admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(BaseUserAdmin, BaseModelAdmin):
    """Unfold-styled administration for the TokenLedger user model."""

    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
        "created_at",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("username",)
    readonly_fields = ("created_at", "updated_at", "last_login", "date_joined")
    fieldsets = (
        (None, {"fields": ("username", "password")} ),
        (
            "Personal Information",
            {"fields": ("first_name", "last_name", "email")},
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            "Important Dates",
            {"fields": ("last_login", "date_joined", "created_at", "updated_at")},
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "usable_password",
                    "password1",
                    "password2",
                ),
            },
        ),
    )


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, BaseModelAdmin):
    """Unfold-styled administration for Django's built-in group model."""

    list_display = ("name",)
    search_fields = ("name",)


@admin.register(AuditLog)
class AuditLogAdmin(BaseModelAdmin):
    """Read-only Unfold administration for audit records."""

    list_display = (
        "created_at",
        "action",
        "model_name",
        "object_id",
        "user",
        "ip_address",
    )
    list_filter = ("action", "model_name", "created_at")
    search_fields = (
        "action",
        "model_name",
        "object_id",
        "description",
        "user__username",
        "user__email",
    )
    readonly_fields = (
        "user",
        "action",
        "model_name",
        "object_id",
        "description",
        "created_at",
        "updated_at",
        "ip_address",
    )
    fieldsets = (
        (
            "Event",
            {"fields": ("action", "description", "created_at", "updated_at")},
        ),
        (
            "Context",
            {"fields": ("user", "model_name", "object_id", "ip_address")},
        ),
    )
    list_select_related = ("user",)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: AuditLog | None = None,
    ) -> bool:
        return False

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: AuditLog | None = None,
    ) -> bool:
        return False


def dashboard_callback(request: HttpRequest, context: dict) -> dict:
    """Build the authenticated staff dashboard from efficient ORM aggregates."""
    if not request.user.is_authenticated or not request.user.is_staff:
        return context

    purchased = CreditPurchase.objects.filter(
        status=CreditPurchase.Status.ACTIVE
    ).aggregate(total=Sum("credit_amount_usd"))["total"] or 0
    allocated = CustomerCreditAllocation.objects.aggregate(
        total=Sum("allocated_credit_usd")
    )["total"] or 0
    received = Transaction.objects.filter(
        transaction_type=Transaction.TransactionType.CUSTOMER_PAYMENT,
        direction=Transaction.Direction.IN,
    ).aggregate(total=Sum("amount"))["total"] or 0
    spent = Transaction.objects.filter(
        transaction_type__in=(
            Transaction.TransactionType.PURCHASE,
            Transaction.TransactionType.EXPENSE,
        ),
        direction=Transaction.Direction.OUT,
    ).aggregate(total=Sum("amount"))["total"] or 0
    profit = CustomerCreditAllocation.objects.aggregate(
        total=Sum("selling_price_usd") - Sum("cost_price_usd")
    )["total"] or 0

    context.update(
        {
            "dashboard_metrics": [
                {"label": "Purchased Credit (USD)", "value": f"{purchased:,.2f}"},
                {"label": "Allocated Credit (USD)", "value": f"{allocated:,.2f}"},
                {
                    "label": "Remaining Available Credit (USD)",
                    "value": f"{purchased - allocated:,.2f}",
                },
                {"label": "Total Customers", "value": f"{Customer.objects.count():,}"},
                {
                    "label": "Active Customers",
                    "value": f"{Customer.objects.filter(status=Customer.Status.ACTIVE).count():,}",
                },
                {"label": "Money Received", "value": f"{received:,.2f}"},
                {"label": "Money Spent", "value": f"{spent:,.2f}"},
                {"label": "Net Cash Flow", "value": f"{received - spent:,.2f}"},
                {"label": "Estimated Profit (USD)", "value": f"{profit:,.2f}"},
            ],
            "recent_transactions": Transaction.objects.select_related(
                "customer", "expense_category"
            ).order_by("-created_at")[:5],
            "recent_allocations": CustomerCreditAllocation.objects.select_related(
                "customer", "provider"
            ).order_by("-created_at")[:5],
            "recent_audit_logs": AuditLog.objects.select_related("user").order_by(
                "-created_at"
            )[:5],
        }
    )
    return context
