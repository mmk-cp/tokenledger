"""Tests for manually maintained exchange rates."""

from datetime import date
from decimal import Decimal

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.core.admin import BaseModelAdmin
from apps.currencies.admin import ExchangeRateAdmin
from apps.currencies.models import ExchangeRate


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
