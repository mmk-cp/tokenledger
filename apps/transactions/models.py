"""Manual financial transaction ledger models."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import TimeStampedModel
from apps.currencies.models import Currency


class ExpenseCategory(TimeStampedModel):
    """A reusable category for organizing business expenses."""

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "Expense Category"
        verbose_name_plural = "Expense Categories"

    def __str__(self) -> str:
        return self.name


class Transaction(TimeStampedModel):
    """A manually recorded financial event."""

    class TransactionType(models.TextChoices):
        PURCHASE = "PURCHASE", "Purchase"
        CUSTOMER_PAYMENT = "CUSTOMER_PAYMENT", "Customer Payment"
        EXPENSE = "EXPENSE", "Expense"
        REFUND = "REFUND", "Refund"
        ADJUSTMENT = "ADJUSTMENT", "Adjustment"

    class Direction(models.TextChoices):
        IN = "IN", "In"
        OUT = "OUT", "Out"

    _REQUIRED_DIRECTIONS = {
        TransactionType.PURCHASE: Direction.OUT,
        TransactionType.CUSTOMER_PAYMENT: Direction.IN,
        TransactionType.EXPENSE: Direction.OUT,
    }

    transaction_type = models.CharField(
        max_length=30,
        choices=TransactionType.choices,
        db_index=True,
    )
    direction = models.CharField(
        max_length=3,
        choices=Direction.choices,
        db_index=True,
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.PROTECT,
        related_name="transactions",
        null=True,
        blank=True,
    )
    wallet = models.ForeignKey(
        "wallets.Wallet",
        on_delete=models.PROTECT,
        related_name="transactions",
        null=True,
        blank=True,
    )
    credit_purchase = models.ForeignKey(
        "credits.CreditPurchase",
        on_delete=models.PROTECT,
        related_name="transactions",
        null=True,
        blank=True,
    )
    allocation = models.ForeignKey(
        "credits.CustomerCreditAllocation",
        on_delete=models.PROTECT,
        related_name="transactions",
        null=True,
        blank=True,
    )
    expense_category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name="transactions",
        null=True,
        blank=True,
    )
    amount = models.DecimalField(
        max_digits=18,
        decimal_places=8,
        validators=[MinValueValidator(Decimal("0.00000001"))],
    )
    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    exchange_rate = models.DecimalField(
        max_digits=18,
        decimal_places=8,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00000001"))],
    )
    converted_amount = models.DecimalField(
        max_digits=24,
        decimal_places=12,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.000000000001"))],
    )
    converted_currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name="converted_transactions",
        null=True,
        blank=True,
    )
    conversion_rate = models.DecimalField(
        max_digits=24,
        decimal_places=12,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.000000000001"))],
    )
    conversion_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    reference = models.CharField(max_length=255, blank=True)
    counterparty = models.CharField(max_length=255, blank=True)
    external_reference = models.CharField(max_length=255, blank=True)
    transaction_date = models.DateField(db_index=True)

    class Meta:
        ordering = ("-transaction_date", "-created_at")
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"
        indexes = [
            models.Index(fields=("transaction_type", "transaction_date")),
            models.Index(fields=("customer", "transaction_date")),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="transaction_amount_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(exchange_rate__gt=0)
                | models.Q(exchange_rate__isnull=True),
                name="transaction_exchange_rate_positive",
            ),
        ]

    def clean(self):
        super().clean()
        errors = {}
        expected_direction = self._REQUIRED_DIRECTIONS.get(self.transaction_type)
        if expected_direction and self.direction != expected_direction:
            errors["direction"] = (
                f"{self.get_transaction_type_display()} transactions must be "
                f"{expected_direction}."
            )

        if self.allocation_id:
            allocation = self.allocation
            if self.customer_id and self.customer_id != allocation.customer_id:
                errors["customer"] = "Customer must match the selected allocation."
            if self.credit_purchase_id and self.credit_purchase_id != allocation.credit_purchase_id:
                errors["credit_purchase"] = (
                    "Credit purchase must match the selected allocation."
                )
            self.customer = allocation.customer
            self.credit_purchase = allocation.credit_purchase

        snapshot_values = (
            self.converted_amount,
            self.converted_currency_id,
            self.conversion_rate,
            self.conversion_date,
        )
        snapshot_complete = all(value is not None for value in snapshot_values)
        if any(value is not None for value in snapshot_values) and not snapshot_complete:
            errors["converted_amount"] = (
                "All valuation snapshot fields must be provided together."
            )
        if snapshot_complete and self.currency_id == self.converted_currency_id:
            if self.conversion_rate != Decimal("1"):
                errors["conversion_rate"] = (
                    "Same-currency snapshots must use a conversion rate of 1."
                )
            if self.converted_amount != self.amount:
                errors["converted_amount"] = (
                    "Same-currency snapshots must match the original amount."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def signed_amount(self) -> Decimal:
        """Return amount with a sign based on the owner-side direction."""
        return self.amount if self.direction == self.Direction.IN else -self.amount

    def __str__(self) -> str:
        return f"{self.get_transaction_type_display()} - {self.amount} {self.currency}"
