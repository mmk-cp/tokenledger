"""Credit purchase and inventory models."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.providers.models import APIEndpoint, Provider
from apps.wallets.models import Wallet


class CreditPurchase(TimeStampedModel):
    """A record of AI API credit purchased by the TokenLedger operator."""

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        EXPIRED = "EXPIRED", "Expired"
        CANCELLED = "CANCELLED", "Cancelled"

    provider = models.ForeignKey(
        Provider,
        on_delete=models.PROTECT,
        related_name="credit_purchases",
    )
    endpoint = models.ForeignKey(
        APIEndpoint,
        on_delete=models.SET_NULL,
        related_name="credit_purchases",
        null=True,
        blank=True,
    )
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.PROTECT,
        related_name="credit_purchases",
    )
    name = models.CharField(max_length=200)
    credit_amount_usd = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    paid_amount = models.DecimalField(
        max_digits=18,
        decimal_places=8,
        validators=[MinValueValidator(Decimal("0.00000001"))],
    )
    paid_currency = models.CharField(max_length=20, db_index=True)
    exchange_rate = models.DecimalField(
        max_digits=18,
        decimal_places=8,
        validators=[MinValueValidator(Decimal("0.00000001"))],
    )
    purchase_date = models.DateField(default=timezone.localdate, db_index=True)
    expire_date = models.DateField(null=True, blank=True, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("-purchase_date", "-created_at")
        verbose_name = "Credit Purchase"
        verbose_name_plural = "Credit Purchases"
        indexes = [
            models.Index(fields=("provider", "status")),
            models.Index(fields=("wallet", "purchase_date")),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(credit_amount_usd__gt=0),
                name="credit_purchase_credit_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(paid_amount__gt=0),
                name="credit_purchase_paid_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(exchange_rate__gt=0),
                name="credit_purchase_rate_positive",
            ),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.endpoint_id and self.provider_id:
            endpoint_provider_id = APIEndpoint.objects.filter(
                pk=self.endpoint_id
            ).values_list("provider_id", flat=True).first()
            if endpoint_provider_id != self.provider_id:
                errors["endpoint"] = "The endpoint must belong to the selected provider."
        if self.expire_date and self.purchase_date and self.expire_date < self.purchase_date:
            errors["expire_date"] = "Expiration date cannot be before purchase date."
        if errors:
            raise ValidationError(errors)

    def __str__(self) -> str:
        return self.name


class CreditBalance(TimeStampedModel):
    """Remaining inventory associated with one credit purchase."""

    purchase = models.OneToOneField(
        CreditPurchase,
        on_delete=models.CASCADE,
        related_name="balance",
    )
    total_credit_usd = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        editable=False,
    )
    used_credit_usd = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    remaining_credit_usd = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        editable=False,
    )

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Credit Balance"
        verbose_name_plural = "Credit Balances"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(used_credit_usd__gte=0),
                name="credit_balance_used_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(remaining_credit_usd__gte=0),
                name="credit_balance_remaining_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(used_credit_usd__lte=models.F("total_credit_usd")),
                name="credit_balance_used_lte_total",
            ),
        ]

    def clean(self):
        super().clean()
        if self.purchase_id and self.used_credit_usd > self.purchase.credit_amount_usd:
            raise ValidationError(
                {"used_credit_usd": "Used credit cannot exceed total purchased credit."}
            )

    def save(self, *args, **kwargs):
        if self.purchase_id:
            total = self.purchase.credit_amount_usd
            if self.used_credit_usd < 0:
                raise ValidationError("Used credit cannot be negative.")
            if self.used_credit_usd > total:
                raise ValidationError(
                    "Used credit cannot exceed total purchased credit."
                )
            self.total_credit_usd = total
            self.remaining_credit_usd = total - self.used_credit_usd
            if kwargs.get("update_fields") is not None:
                kwargs["update_fields"] = set(kwargs["update_fields"]) | {
                    "total_credit_usd",
                    "remaining_credit_usd",
                }
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Balance for {self.purchase.name}"
