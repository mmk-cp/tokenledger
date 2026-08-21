"""Shared Unfold admin helpers and dashboard context."""

from datetime import timedelta
from decimal import Decimal

from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.db.models import F, Func, IntegerField, Sum, Value
from django.http import HttpRequest
from django.utils import timezone
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm

from apps.core.forms import UserChangeForm, UserCreationForm
from apps.core.models import AuditLog, User
from apps.currencies.services import CurrencyConversionError, convert_amount
from apps.credits.models import CreditBalance, CustomerCreditAllocation, CreditPurchase
from apps.customers.models import Customer
from apps.transactions.models import Transaction


class BaseModelAdmin(ModelAdmin):
    """Base class for all TokenLedger model administration classes."""

    list_per_page = 50
    save_on_top = True
    warn_unsaved_form = True


DASHBOARD_CURRENCY = "USD"


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


def _converted_transaction_total(
    queryset,
    conversion_factors: dict[tuple[str, object], Decimal | None],
) -> Decimal:
    """Return a dashboard-currency total, ignoring rows without a usable rate."""
    total = Decimal("0")

    for transaction in queryset.values(
        "amount",
        "currency__code",
        "converted_amount",
        "converted_currency__code",
        "transaction_date",
    ).iterator():
        if (
            transaction["converted_amount"] is not None
            and transaction["converted_currency__code"] == DASHBOARD_CURRENCY
        ):
            total += transaction["converted_amount"]
            continue
        rate_key = (transaction["currency__code"], transaction["transaction_date"])
        if rate_key not in conversion_factors:
            try:
                conversion_factors[rate_key] = convert_amount(
                    amount=Decimal("1"),
                    from_currency=transaction["currency__code"],
                    to_currency=DASHBOARD_CURRENCY,
                    date=transaction["transaction_date"],
                )
            except CurrencyConversionError:
                conversion_factors[rate_key] = None

        factor = conversion_factors[rate_key]
        if factor is not None:
            total += transaction["amount"] * factor

    return total


def _converted_purchase_cost_total(
    queryset,
    conversion_factors: dict[tuple[str, object], Decimal | None],
) -> Decimal:
    """Return active purchase cost in USD, preferring stored valuation snapshots."""
    total = Decimal("0")
    for purchase in queryset.values(
        "paid_amount",
        "paid_currency__code",
        "converted_amount",
        "converted_currency__code",
        "purchase_date",
    ).iterator():
        if (
            purchase["converted_amount"] is not None
            and purchase["converted_currency__code"] == DASHBOARD_CURRENCY
        ):
            total += purchase["converted_amount"]
            continue

        rate_key = (purchase["paid_currency__code"], purchase["purchase_date"])
        if rate_key not in conversion_factors:
            try:
                conversion_factors[rate_key] = convert_amount(
                    amount=Decimal("1"),
                    from_currency=purchase["paid_currency__code"],
                    to_currency=DASHBOARD_CURRENCY,
                    date=purchase["purchase_date"],
                )
            except CurrencyConversionError:
                conversion_factors[rate_key] = None

        factor = conversion_factors[rate_key]
        if factor is not None:
            total += purchase["paid_amount"] * factor
    return total


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
    customer_credit_value = CustomerCreditAllocation.objects.filter(
        status=CustomerCreditAllocation.Status.ACTIVE
    ).aggregate(total=Sum("remaining_credit_usd"))["total"] or 0
    available_credit = CreditBalance.objects.aggregate(
        total=Sum("remaining_credit_usd")
    )["total"] or 0
    cost_basis = CustomerCreditAllocation.objects.aggregate(
        total=Sum("cost_price_usd")
    )["total"] or 0
    conversion_factors: dict[tuple[str, object], Decimal | None] = {}
    active_purchases = CreditPurchase.objects.filter(status=CreditPurchase.Status.ACTIVE)
    total_purchase_cost = _converted_purchase_cost_total(
        active_purchases,
        conversion_factors,
    )
    total_credit_purchased = active_purchases.aggregate(
        total=Sum("credit_amount_usd")
    )["total"] or Decimal("0")
    average_purchase_cost = (
        total_purchase_cost / total_credit_purchased
        if total_credit_purchased
        else Decimal("0")
    )
    received = _converted_transaction_total(
        Transaction.objects.filter(
            transaction_type=Transaction.TransactionType.CUSTOMER_PAYMENT,
            direction=Transaction.Direction.IN,
        ),
        conversion_factors,
    )
    spent = _converted_transaction_total(
        Transaction.objects.filter(
            transaction_type__in=(
                Transaction.TransactionType.PURCHASE,
                Transaction.TransactionType.EXPENSE,
            ),
            direction=Transaction.Direction.OUT,
        ),
        conversion_factors,
    )
    profit = CustomerCreditAllocation.objects.aggregate(
        total=Sum("selling_price_usd") - Sum("cost_price_usd")
    )["total"] or 0
    today = timezone.localdate()
    expiration_queryset = CustomerCreditAllocation.objects.filter(
        status=CustomerCreditAllocation.Status.ACTIVE,
        expire_date__isnull=False,
    ).select_related("customer", "provider").annotate(
        days_remaining=Func(
            F("expire_date"),
            Value(today),
            function="DATEDIFF",
            output_field=IntegerField(),
        )
    )

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
                {
                    "label": "Total Customer Credit Value (USD)",
                    "value": f"{customer_credit_value:,.2f}",
                },
                {
                    "label": "Total Available Credit (USD)",
                    "value": f"{available_credit:,.2f}",
                },
                {"label": "Total Cost Basis (USD)", "value": f"{cost_basis:,.2f}"},
                {
                    "label": "Total Purchased Cost (USD)",
                    "value": f"{total_purchase_cost:,.2f}",
                },
                {
                    "label": "Total Credit Purchased (USD)",
                    "value": f"{total_credit_purchased:,.2f}",
                },
                {
                    "label": "Average Purchase Cost",
                    "value": f"{average_purchase_cost:,.6f}",
                },
                {
                    "label": f"Money Received ({DASHBOARD_CURRENCY})",
                    "value": f"{received:,.2f}",
                },
                {
                    "label": f"Money Spent ({DASHBOARD_CURRENCY})",
                    "value": f"{spent:,.2f}",
                },
                {
                    "label": f"Net Cash Flow ({DASHBOARD_CURRENCY})",
                    "value": f"{received - spent:,.2f}",
                },
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
            "expiring_credits": expiration_queryset.filter(
                expire_date__gte=today,
                expire_date__lte=today + timedelta(days=30),
            ).order_by("expire_date", "customer__name")[:10],
            "expired_credits": expiration_queryset.filter(
                expire_date__lt=today,
            ).order_by("-expire_date", "customer__name")[:10],
        }
    )
    return context
