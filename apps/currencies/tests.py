"""Tests for manually maintained exchange rates."""

from datetime import date
from decimal import Decimal

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.core.admin import BaseModelAdmin
from apps.currencies.admin import ExchangeRateAdmin
from apps.currencies.models import ExchangeRate
from apps.currencies.services import (
    InvalidAmountError,
    MissingExchangeRateError,
    convert_amount,
)


class ExchangeRateTests(TestCase):
    def test_decimal_rate_is_stored_exactly(self):
        exchange_rate = ExchangeRate.objects.create(
            base_currency="usdt",
            target_currency="irr",
            rate=Decimal("95000.123456789012"),
            effective_date=date.today(),
        )

        exchange_rate.refresh_from_db()
        self.assertEqual(exchange_rate.rate, Decimal("95000.123456789012"))
        self.assertEqual(exchange_rate.base_currency, "USDT")
        self.assertEqual(exchange_rate.target_currency, "IRR")

    def test_rate_must_be_positive(self):
        exchange_rate = ExchangeRate(
            base_currency="USDT",
            target_currency="USD",
            rate=Decimal("0"),
            effective_date=date.today(),
        )

        with self.assertRaises(ValidationError):
            exchange_rate.full_clean()

    def test_base_and_target_currency_must_differ(self):
        exchange_rate = ExchangeRate(
            base_currency="usd",
            target_currency="USD",
            rate=Decimal("1"),
            effective_date=date.today(),
        )

        with self.assertRaises(ValidationError) as error:
            exchange_rate.full_clean()

        self.assertIn("target_currency", error.exception.message_dict)

    def test_admin_uses_unfold_base_model_admin(self):
        self.assertTrue(admin.site.is_registered(ExchangeRate))
        self.assertTrue(issubclass(ExchangeRateAdmin, BaseModelAdmin))


class CurrencyConversionTests(TestCase):
    def create_rate(self, base, target, rate, effective_date, is_active=True):
        return ExchangeRate.objects.create(
            base_currency=base,
            target_currency=target,
            rate=Decimal(rate),
            effective_date=effective_date,
            is_active=is_active,
        )

    def test_same_currency_returns_unchanged_decimal(self):
        result = convert_amount(
            amount=100,
            from_currency="usd",
            to_currency="USD",
            date=date(2026, 8, 21),
        )

        self.assertEqual(result, Decimal("100"))
        self.assertIsInstance(result, Decimal)

    def test_direct_conversion(self):
        self.create_rate("USDT", "USD", "1.01", date(2026, 8, 1))

        result = convert_amount(
            amount=Decimal("100"),
            from_currency="USDT",
            to_currency="USD",
            date=date(2026, 8, 21),
        )

        self.assertEqual(result, Decimal("101.000000000000"))

    def test_reverse_conversion(self):
        self.create_rate("USDT", "USD", "2", date(2026, 8, 1))

        result = convert_amount(
            amount=Decimal("100"),
            from_currency="USD",
            to_currency="USDT",
            date=date(2026, 8, 21),
        )

        self.assertEqual(result, Decimal("50"))

    def test_historical_rate_selection(self):
        self.create_rate("USDT", "IRR", "90000", date(2026, 7, 1))
        self.create_rate("USDT", "IRR", "95000", date(2026, 8, 1))
        self.create_rate("USDT", "IRR", "99000", date(2026, 9, 1))
        self.create_rate(
            "USDT", "IRR", "97000", date(2026, 8, 15), is_active=False
        )

        result = convert_amount(
            amount=Decimal("2"),
            from_currency="USDT",
            to_currency="IRR",
            date=date(2026, 8, 21),
        )

        self.assertEqual(result, Decimal("190000.000000000000"))

    def test_missing_rate_raises_clear_error(self):
        with self.assertRaisesMessage(
            MissingExchangeRateError,
            "No active exchange rate from BTC to USD",
        ):
            convert_amount(
                amount=Decimal("1"),
                from_currency="BTC",
                to_currency="USD",
                date=date(2026, 8, 21),
            )

    def test_decimal_precision_and_float_rejection(self):
        self.create_rate("ETH", "USD", "1.123456789012", date(2026, 8, 1))

        result = convert_amount(
            amount=Decimal("0.123456789012"),
            from_currency="ETH",
            to_currency="USD",
            date=date(2026, 8, 21),
        )

        self.assertEqual(result, Decimal("0.138698367765153483936144"))
        with self.assertRaises(InvalidAmountError):
            convert_amount(
                amount=0.1,
                from_currency="ETH",
                to_currency="USD",
                date=date(2026, 8, 21),
            )
