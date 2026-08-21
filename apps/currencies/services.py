"""Reusable Decimal-only currency conversion services."""

from datetime import date as Date
from decimal import Decimal

from apps.currencies.models import Currency, ExchangeRate


class CurrencyConversionError(Exception):
    """Base exception for currency conversion failures."""


class InvalidCurrencyError(CurrencyConversionError):
    """Raised when a currency code is missing or invalid."""


class InvalidAmountError(CurrencyConversionError):
    """Raised when an amount cannot be handled without floating-point input."""


class MissingExchangeRateError(CurrencyConversionError):
    """Raised when no eligible direct or reverse exchange rate exists."""


def _normalize_currency(currency: str | Currency) -> str:
    if isinstance(currency, Currency):
        return currency.code
    if not isinstance(currency, str):
        raise InvalidCurrencyError("Currency must be a string.")

    normalized = currency.strip().upper()
    if not normalized or len(normalized) > 20 or not normalized.isalnum():
        raise InvalidCurrencyError(f'Invalid currency code: "{currency}".')
    return normalized


def _to_decimal(amount: Decimal | int) -> Decimal:
    if isinstance(amount, bool) or isinstance(amount, float):
        raise InvalidAmountError("Amount must use Decimal or integer values, not float.")
    if isinstance(amount, Decimal):
        return amount
    if isinstance(amount, int):
        return Decimal(amount)
    raise InvalidAmountError("Amount must be a valid Decimal or integer value.")


def convert_amount(
    *,
    amount: Decimal | int,
    from_currency: str | Currency,
    to_currency: str | Currency,
    date: Date,
) -> Decimal:
    """Convert an amount using the latest active rate effective by a given date."""
    decimal_amount = _to_decimal(amount)
    source = _normalize_currency(from_currency)
    target = _normalize_currency(to_currency)

    if not isinstance(date, Date):
        raise CurrencyConversionError("Conversion date must be a date object.")
    if source == target:
        return decimal_amount

    direct_rate = (
        ExchangeRate.objects.filter(
            base_currency__code=source,
            target_currency__code=target,
            effective_date__lte=date,
            is_active=True,
        )
        .order_by("-effective_date", "-created_at")
        .values_list("rate", flat=True)
        .first()
    )
    if direct_rate is not None:
        return decimal_amount * direct_rate

    reverse_rate = (
        ExchangeRate.objects.filter(
            base_currency__code=target,
            target_currency__code=source,
            effective_date__lte=date,
            is_active=True,
        )
        .order_by("-effective_date", "-created_at")
        .values_list("rate", flat=True)
        .first()
    )
    if reverse_rate is not None:
        return decimal_amount / reverse_rate

    raise MissingExchangeRateError(
        f"No active exchange rate from {source} to {target} exists on or before {date}."
    )
