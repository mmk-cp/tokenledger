"""Manually maintained currency exchange rates."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class Currency(TimeStampedModel):
    """A dynamic fiat or cryptocurrency available to TokenLedger."""

    class CurrencyType(models.TextChoices):
        FIAT = "FIAT", _("Fiat")
        CRYPTO = "CRYPTO", _("Crypto")

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=20, blank=True)
    currency_type = models.CharField(
        max_length=10,
        choices=CurrencyType.choices,
        db_index=True,
    )
    decimal_places = models.PositiveSmallIntegerField(default=2)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ("code",)
        verbose_name = _("Currency")
        verbose_name_plural = _("Currencies")

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.code


class ExchangeRate(TimeStampedModel):
    """A manually entered exchange rate effective on a specific date."""

    base_currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name="base_exchange_rates",
    )
    target_currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name="target_exchange_rates",
    )
    rate = models.DecimalField(
        max_digits=24,
        decimal_places=12,
        validators=[MinValueValidator(Decimal("0.000000000001"))],
    )
    effective_date = models.DateField(db_index=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ("-effective_date", "base_currency", "target_currency")
        verbose_name = _("Exchange Rate")
        verbose_name_plural = _("Exchange Rates")
        indexes = [
            models.Index(
                fields=("base_currency", "target_currency", "effective_date"),
                name="currencies__base_cu_4607f0_idx",
            ),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.base_currency and self.target_currency:
            if self.base_currency_id == self.target_currency_id:
                errors["target_currency"] = (
                    "Base currency and target currency must be different."
                )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.base_currency} to {self.target_currency} ({self.rate})"
