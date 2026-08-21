"""Tests for relational transaction currencies."""

from datetime import date
from decimal import Decimal

from django.contrib import admin
from django.db.models.deletion import ProtectedError
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase

from apps.core.models import AuditLog, User
from apps.currencies.models import Currency
from apps.transactions.admin import TransactionAdmin
from apps.transactions.models import Transaction


class TransactionCurrencyTests(TestCase):
    def setUp(self):
        self.currency = Currency.objects.get(code="USD")
        self.transaction = Transaction.objects.create(
            transaction_type=Transaction.TransactionType.CUSTOMER_PAYMENT,
            direction=Transaction.Direction.IN,
            amount=Decimal("25.00"),
            currency=self.currency,
            exchange_rate=Decimal("1.23456789"),
            transaction_date=date.today(),
        )

    def test_transaction_uses_currency_relation_and_preserves_exchange_rate(self):
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.currency.code, "USD")
        self.assertEqual(self.transaction.exchange_rate, Decimal("1.23456789"))

    def test_currency_delete_is_protected(self):
        with self.assertRaises(ProtectedError):
            self.currency.delete()

    def test_existing_audit_logging_still_tracks_transaction(self):
        self.assertTrue(
            AuditLog.objects.filter(
                action="CREATE",
                model_name="Transaction",
                object_id=self.transaction.pk,
            ).exists()
        )

    def test_add_form_offers_only_active_currencies(self):
        inactive = Currency.objects.create(
            code="OLD",
            name="Old Currency",
            currency_type=Currency.CurrencyType.FIAT,
            decimal_places=2,
            is_active=False,
        )
        transaction_admin = TransactionAdmin(Transaction, admin.site)
        request = RequestFactory().get("/admin/transactions/transaction/add/")
        request.user = User.objects.create_superuser(
            username="transaction-admin",
            email="transaction-admin@example.com",
            password="test-password",
        )

        form = transaction_admin.get_form(request)
        queryset = form.base_fields["currency"].queryset
        self.assertTrue(queryset.filter(pk=self.currency.pk).exists())
        self.assertFalse(queryset.filter(pk=inactive.pk).exists())

    def test_transaction_without_snapshot_works(self):
        self.assertIsNone(self.transaction.converted_amount)

    def test_complete_snapshot_works(self):
        usdt = Currency.objects.get(code="USDT")
        self.transaction.converted_amount = Decimal("30.00")
        self.transaction.converted_currency = usdt
        self.transaction.conversion_rate = Decimal("1.20")
        self.transaction.conversion_date = date.today()
        self.transaction.save()
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.converted_currency, usdt)

    def test_partial_snapshot_is_rejected(self):
        self.transaction.converted_amount = Decimal("25.00")
        with self.assertRaises(ValidationError):
            self.transaction.full_clean()

    def test_same_currency_snapshot_requires_identity_values(self):
        self.transaction.converted_amount = Decimal("25.00")
        self.transaction.converted_currency = self.currency
        self.transaction.conversion_rate = Decimal("1.10")
        self.transaction.conversion_date = date.today()
        with self.assertRaises(ValidationError):
            self.transaction.full_clean()

        self.transaction.conversion_rate = Decimal("1")
        self.transaction.converted_amount = Decimal("24.99")
        with self.assertRaises(ValidationError):
            self.transaction.full_clean()
