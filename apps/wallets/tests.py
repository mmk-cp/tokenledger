"""Tests for relational wallet currencies."""

from django.contrib import admin
from django.db.models.deletion import ProtectedError
from django.test import RequestFactory, TestCase

from apps.core.models import User
from apps.currencies.models import Currency
from apps.wallets.admin import WalletAdmin
from apps.wallets.models import Wallet


class WalletCurrencyTests(TestCase):
    def setUp(self):
        self.currency = Currency.objects.get(code="USDT")
        self.wallet = Wallet.objects.create(
            name="Treasury Wallet",
            currency=self.currency,
            network="TRC20",
            address="wallet-currency-test-address",
        )

    def test_wallet_uses_currency_relation(self):
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.currency, self.currency)
        self.assertEqual(self.wallet.currency.code, "USDT")

    def test_currency_delete_is_protected(self):
        with self.assertRaises(ProtectedError):
            self.currency.delete()

    def test_wallet_admin_uses_related_currency(self):
        wallet_admin = WalletAdmin(Wallet, admin.site)
        request = RequestFactory().get("/admin/wallets/wallet/")
        request.user = User.objects.create_superuser(
            username="wallet-admin",
            email="wallet-admin@example.com",
            password="test-password",
        )

        self.assertIn("currency__code", wallet_admin.search_fields)
        self.assertIn("currency", wallet_admin.list_filter)
        self.assertIn("currency", wallet_admin.list_select_related)

    def test_add_form_offers_only_active_currencies(self):
        inactive = Currency.objects.create(
            code="OLD",
            name="Inactive Currency",
            currency_type=Currency.CurrencyType.FIAT,
            decimal_places=2,
            is_active=False,
        )
        wallet_admin = WalletAdmin(Wallet, admin.site)
        request = RequestFactory().get("/admin/wallets/wallet/add/")
        request.user = User.objects.create_superuser(
            username="wallet-form-admin",
            email="wallet-form-admin@example.com",
            password="test-password",
        )

        form = wallet_admin.get_form(request)
        queryset = form.base_fields["currency"].queryset
        self.assertTrue(queryset.filter(pk=self.currency.pk).exists())
        self.assertFalse(queryset.filter(pk=inactive.pk).exists())
