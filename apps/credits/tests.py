"""Tests for credit purchase currency relations and snapshots."""

from decimal import Decimal

from django.contrib import admin
from django.db.models.deletion import ProtectedError
from django.test import RequestFactory, TestCase

from apps.core.models import User
from apps.credits.admin import CreditPurchaseAdmin
from apps.credits.models import CreditBalance, CreditPurchase, CustomerCreditAllocation
from apps.currencies.models import Currency
from apps.customers.models import Customer
from apps.providers.models import Provider
from apps.wallets.models import Wallet


class CreditPurchaseCurrencyTests(TestCase):
    def setUp(self):
        self.currency = Currency.objects.get(code="USDT")
        self.provider = Provider.objects.create(name="Purchase Provider", slug="purchase-provider")
        self.wallet = Wallet.objects.create(
            name="Purchase Wallet",
            currency=self.currency,
            network="TRC20",
            address="purchase-currency-wallet-address",
        )
        self.purchase = CreditPurchase.objects.create(
            provider=self.provider,
            wallet=self.wallet,
            name="Snapshot Purchase",
            credit_amount_usd=Decimal("100.00"),
            paid_amount=Decimal("50.00"),
            paid_currency=self.currency,
            exchange_rate=Decimal("1.25"),
        )

    def test_paid_currency_is_a_relation(self):
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.paid_currency.code, "USDT")

    def test_currency_delete_is_protected(self):
        with self.assertRaises(ProtectedError):
            self.currency.delete()

    def test_exchange_rate_snapshot_and_allocation_cost_are_unchanged(self):
        balance = CreditBalance.objects.create(
            purchase=self.purchase,
            used_credit_usd=Decimal("0.00"),
        )
        customer = Customer.objects.create(name="Snapshot Customer")
        allocation = CustomerCreditAllocation.objects.create(
            customer=customer,
            credit_purchase=self.purchase,
            allocated_credit_usd=Decimal("40.00"),
            selling_price_usd=Decimal("60.00"),
        )

        self.purchase.refresh_from_db()
        allocation.refresh_from_db()
        self.assertEqual(self.purchase.exchange_rate, Decimal("1.25"))
        self.assertEqual(allocation.cost_price_usd, Decimal("25.00"))
        self.assertEqual(balance.remaining_credit_usd, Decimal("100.00"))

    def test_add_form_offers_only_active_currencies(self):
        inactive = Currency.objects.create(
            code="OLD",
            name="Old Currency",
            currency_type=Currency.CurrencyType.FIAT,
            decimal_places=2,
            is_active=False,
        )
        purchase_admin = CreditPurchaseAdmin(CreditPurchase, admin.site)
        request = RequestFactory().get("/admin/credits/creditpurchase/add/")
        request.user = User.objects.create_superuser(
            username="purchase-admin",
            email="purchase-admin@example.com",
            password="test-password",
        )

        form = purchase_admin.get_form(request)
        queryset = form.base_fields["paid_currency"].queryset
        self.assertTrue(queryset.filter(pk=self.currency.pk).exists())
        self.assertFalse(queryset.filter(pk=inactive.pk).exists())
