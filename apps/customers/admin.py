"""Unfold admin registration for customers."""

from django.contrib import admin
from django.db.models import Count, DecimalField, Min, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpRequest
from unfold.admin import TabularInline

from apps.core.admin import BaseModelAdmin
from apps.credits.models import CustomerCreditAllocation
from apps.customer_credentials.models import CustomerCredential
from apps.customers.models import Customer
from apps.transactions.models import Transaction


class CustomerAllocationInline(TabularInline):
    model = CustomerCreditAllocation
    extra = 0
    can_delete = False
    fields = ("provider", "allocated_credit_usd", "remaining_credit_usd", "status", "expire_date")
    readonly_fields = fields
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


class CustomerTransactionInline(TabularInline):
    model = Transaction
    extra = 0
    can_delete = False
    fields = ("transaction_type", "direction", "amount", "currency", "transaction_date", "reference")
    readonly_fields = fields
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


class CustomerCredentialInline(TabularInline):
    model = CustomerCredential
    extra = 0
    can_delete = False
    fields = (
        "provider",
        "endpoint",
        "credit_allocation",
        "assigned_credit_usd",
        "status",
        "expire_date",
    )
    readonly_fields = fields
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Customer)
class CustomerAdmin(BaseModelAdmin):
    """Unfold administration for customer records."""

    list_display = (
        "name",
        "company_name",
        "status",
        "total_allocated_credit_display",
        "remaining_credit_display",
        "total_payments_received_display",
        "active_credentials_display",
        "next_credit_expiration_display",
        "active_allocations_display",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("name", "company_name", "email", "phone", "telegram")
    ordering = ("-created_at",)
    readonly_fields = (
        "credit_summary",
        "financial_summary",
        "credential_summary",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        (
            "Customer",
            {"fields": ("name", "company_name", "status")},
        ),
        (
            "Contact Information",
            {"fields": ("email", "phone", "telegram")},
        ),
        (
            "Credit Summary",
            {"fields": ("credit_summary",)},
        ),
        (
            "Financial Summary",
            {"fields": ("financial_summary",)},
        ),
        (
            "Credential Summary",
            {"fields": ("credential_summary",)},
        ),
        ("Internal Notes", {"fields": ("notes",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
    inlines = (
        CustomerAllocationInline,
        CustomerTransactionInline,
        CustomerCredentialInline,
    )

    def get_queryset(self, request: HttpRequest):
        decimal_output = DecimalField(max_digits=20, decimal_places=8)
        allocation_totals = CustomerCreditAllocation.objects.filter(
            customer=OuterRef("pk")
        ).values("customer")
        transaction_totals = Transaction.objects.filter(
            customer=OuterRef("pk")
        ).values("customer")
        credential_totals = CustomerCredential.objects.filter(
            customer=OuterRef("pk"),
            status=CustomerCredential.Status.ACTIVE,
        ).values("customer")
        return super().get_queryset(request).annotate(
            admin_total_allocated=Coalesce(
                Subquery(
                    allocation_totals.annotate(
                        total=Sum("allocated_credit_usd")
                    ).values("total")[:1],
                    output_field=decimal_output,
                ),
                Value(0),
                output_field=decimal_output,
            ),
            admin_remaining_credit=Coalesce(
                Subquery(
                    allocation_totals.filter(
                        status=CustomerCreditAllocation.Status.ACTIVE
                    ).annotate(total=Sum("remaining_credit_usd")).values("total")[:1],
                    output_field=decimal_output,
                ),
                Value(0),
                output_field=decimal_output,
            ),
            admin_payments_received=Coalesce(
                Subquery(
                    transaction_totals.filter(
                        transaction_type=Transaction.TransactionType.CUSTOMER_PAYMENT,
                        direction=Transaction.Direction.IN,
                    ).annotate(total=Sum("amount")).values("total")[:1],
                    output_field=decimal_output,
                ),
                Value(0),
                output_field=decimal_output,
            ),
            admin_next_expiration=Min(
                "credit_allocations__expire_date",
                filter=Q(
                    credit_allocations__status=CustomerCreditAllocation.Status.ACTIVE,
                    credit_allocations__expire_date__isnull=False,
                ),
            ),
            admin_active_allocations=Count(
                "credit_allocations",
                filter=Q(
                    credit_allocations__status=CustomerCreditAllocation.Status.ACTIVE
                ),
                distinct=True,
            ),
            admin_active_credentials=Coalesce(
                Subquery(
                    credential_totals.annotate(total=Count("id")).values("total")[:1]
                ),
                Value(0),
            ),
            admin_next_credential_expiration=Subquery(
                credential_totals.filter(expire_date__isnull=False)
                .order_by("expire_date")
                .values("expire_date")[:1]
            ),
        )

    @admin.display(description="Total Allocated Credit (USD)", ordering="admin_total_allocated")
    def total_allocated_credit_display(self, obj: Customer):
        return obj.admin_total_allocated

    @admin.display(description="Remaining Credit (USD)", ordering="admin_remaining_credit")
    def remaining_credit_display(self, obj: Customer):
        return obj.admin_remaining_credit

    @admin.display(description="Payments Received", ordering="admin_payments_received")
    def total_payments_received_display(self, obj: Customer):
        return obj.admin_payments_received

    @admin.display(description="Active Credentials", ordering="admin_active_credentials")
    def active_credentials_display(self, obj: Customer):
        return obj.admin_active_credentials

    @admin.display(description="Next Credit Expiration", ordering="admin_next_expiration")
    def next_credit_expiration_display(self, obj: Customer):
        return obj.admin_next_expiration or "-"

    @admin.display(description="Active Allocations", ordering="admin_active_allocations")
    def active_allocations_display(self, obj: Customer):
        return obj.admin_active_allocations

    @admin.display(description="Credit Summary")
    def credit_summary(self, obj: Customer | None):
        if not obj:
            return "Available after the customer is saved."
        decimal_output = DecimalField(max_digits=20, decimal_places=8)
        summary = obj.credit_allocations.aggregate(
            total_allocated=Coalesce(
                Sum("allocated_credit_usd"), Value(0), output_field=decimal_output
            ),
            remaining_active=Coalesce(
                Sum(
                    "remaining_credit_usd",
                    filter=Q(status=CustomerCreditAllocation.Status.ACTIVE),
                ),
                Value(0),
                output_field=decimal_output,
            ),
            active_count=Count(
                "id", filter=Q(status=CustomerCreditAllocation.Status.ACTIVE)
            ),
        )
        return (
            f'Total allocated: {summary["total_allocated"]:.2f} USD | '
            f'Remaining active: {summary["remaining_active"]:.2f} USD | '
            f'Active allocations: {summary["active_count"]}'
        )

    @admin.display(description="Financial Summary")
    def financial_summary(self, obj: Customer | None):
        if not obj:
            return "Available after the customer is saved."
        summary = obj.transactions.aggregate(
            payments=Coalesce(
                Sum(
                    "amount",
                    filter=Q(
                        transaction_type=Transaction.TransactionType.CUSTOMER_PAYMENT,
                        direction=Transaction.Direction.IN,
                    ),
                ),
                Value(0),
                output_field=DecimalField(max_digits=20, decimal_places=8),
            ),
            refunds=Coalesce(
                Sum("amount", filter=Q(transaction_type=Transaction.TransactionType.REFUND)),
                Value(0),
                output_field=DecimalField(max_digits=20, decimal_places=8),
            ),
        )
        return (
            f'Payments received: {summary["payments"]:.2f} | '
            f'Refunds: {summary["refunds"]:.2f} | '
            f'Net paid: {summary["payments"] - summary["refunds"]:.2f}'
        )

    @admin.display(description="Credential Summary")
    def credential_summary(self, obj: Customer | None):
        if not obj:
            return "Available after the customer is saved."
        summary = obj.credentials.aggregate(
            active_count=Count(
                "id", filter=Q(status=CustomerCredential.Status.ACTIVE)
            ),
            active_credit=Coalesce(
                Sum(
                    "assigned_credit_usd",
                    filter=Q(status=CustomerCredential.Status.ACTIVE),
                ),
                Value(0),
                output_field=DecimalField(max_digits=20, decimal_places=2),
            ),
            next_expiration=Min(
                "expire_date",
                filter=Q(
                    status=CustomerCredential.Status.ACTIVE,
                    expire_date__isnull=False,
                ),
            ),
        )
        next_expiration = summary["next_expiration"] or "-"
        return (
            f'Active credentials: {summary["active_count"]} | '
            f'Assigned credit: {summary["active_credit"]:.2f} USD | '
            f'Next expiration: {next_expiration}'
        )
