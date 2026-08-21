"""Manually maintained currency exchange rates."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import TimeStampedModel


class ExchangeRate(TimeStampedModel):
    """A manually entered exchange rate effective on a specific date."""

    base_currency = models.CharField(max_length=20)
    target_currency = models.CharField(max_length=20)
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
        verbose_name = "Exchange Rate"
        verbose_name_plural = "Exchange Rates"
        indexes = [
            models.Index(fields=("base_currency", "target_currency", "effective_date")),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.base_currency and self.target_currency:
            if self.base_currency.strip().upper() == self.target_currency.strip().upper():
                errors["target_currency"] = (
                    "Base currency and target currency must be different."
                )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.base_currency = self.base_currency.strip().upper()
        self.target_currency = self.target_currency.strip().upper()
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.base_currency} to {self.target_currency} ({self.rate})"
