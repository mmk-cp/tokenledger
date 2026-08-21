from datetime import date
from decimal import Decimal

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.test import RequestFactory, TestCase

from apps.core.models import User
from apps.credits.models import CreditBalance, CreditPurchase, CustomerCreditAllocation
from apps.customer_credentials.models import CustomerCredential
from apps.currencies.models import Currency
from apps.customers.models import Customer
from apps.customers.admin import CustomerAdmin
from apps.providers.models import APIEndpoint, Provider
from apps.wallets.models import Wallet


class CustomerCredentialAllocationTests(TestCase):
    def setUp(self):
        self.currency = Currency.objects.get(code="USDT")
        self.provider = Provider.objects.create(name="Credential Provider", slug="credential-provider")
        self.endpoint = APIEndpoint.objects.create(provider=self.provider, name="Primary", base_url="https://example.com", api_key="secret-key")
        self.customer = Customer.objects.create(name="Credential Customer", email="credential@example.com")
        self.wallet = Wallet.objects.create(name="Credential Wallet", currency=self.currency, network="TRC20", address="credential-wallet-address")
        self.purchase = CreditPurchase.objects.create(provider=self.provider, wallet=self.wallet, name="Credential Purchase", credit_amount_usd=Decimal("100.00"), paid_amount=Decimal("50.00"), paid_currency=self.currency, exchange_rate=Decimal("1.00"))
        CreditBalance.objects.create(purchase=self.purchase, used_credit_usd=Decimal("0.00"))
        self.allocation = CustomerCreditAllocation.objects.create(customer=self.customer, credit_purchase=self.purchase, allocated_credit_usd=Decimal("20.00"), selling_price_usd=Decimal("25.00"))

    def credential(self, **kwargs):
        values = dict(customer=self.customer, provider=self.provider, endpoint=self.endpoint, encrypted_api_key="credential-secret", start_date=date.today())
        values.update(kwargs)
        return CustomerCredential(**values)

    def test_optional_and_valid_allocation(self):
        self.credential().full_clean()
        self.credential(credit_allocation=self.allocation).full_clean()

    def test_allocation_customer_and_provider_must_match(self):
        other_customer = Customer.objects.create(name="Other", email="other@example.com")
        with self.assertRaises(ValidationError):
            self.credential(credit_allocation=self.allocation, customer=other_customer).full_clean()
        other_provider = Provider.objects.create(name="Other Provider", slug="other-provider")
        with self.assertRaises(ValidationError):
            self.credential(credit_allocation=self.allocation, provider=other_provider).full_clean()

    def test_allocation_delete_is_protected(self):
        self.credential(credit_allocation=self.allocation).save()
        with self.assertRaises(ProtectedError):
            self.allocation.delete()

    def test_customer_admin_credential_annotations_and_summary(self):
        expiration = date(2026, 9, 10)
        self.credential(
            credit_allocation=self.allocation,
            assigned_credit_usd=Decimal("20.00"),
            expire_date=expiration,
        ).save()
        self.credential(
            status=CustomerCredential.Status.CANCELLED,
            assigned_credit_usd=Decimal("5.00"),
        ).save()
        customer_admin = CustomerAdmin(Customer, admin.site)
        request = RequestFactory().get("/admin/customers/customer/")
        request.user = User(is_staff=True, is_active=True)
        customer = customer_admin.get_queryset(request).get(pk=self.customer.pk)

        self.assertEqual(customer.admin_active_credentials, 1)
        self.assertEqual(customer.admin_next_credential_expiration, expiration)
        summary = customer_admin.credential_summary(self.customer)
        self.assertIn("Active credentials: 1", summary)
        self.assertIn("Assigned credit: 20.00 USD", summary)
        self.assertIn("Next expiration: 2026-09-10", summary)
