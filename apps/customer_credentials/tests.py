from datetime import date
from decimal import Decimal

from django.contrib import admin
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.test import RequestFactory, TestCase

from apps.core.models import AuditLog, User
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
        self.allocation = CustomerCreditAllocation.objects.create(customer=self.customer, credit_purchase=self.purchase, allocated_credit_usd=Decimal("20.00"), selling_price_usd=Decimal("25.00"))

    def credential(self, **kwargs):
        values = dict(customer=self.customer, provider=self.provider, endpoint=self.endpoint, api_key="credential-secret", start_date=date.today())
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
            expire_date=expiration,
        ).save()
        self.credential(
            status=CustomerCredential.Status.CANCELLED,
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


class APIKeyAdminSecurityTests(TestCase):
    def setUp(self):
        self.raw_endpoint_key = "sk-endpoint-super-secret"
        self.raw_customer_key = "sk-customer-super-secret"
        self.provider = Provider.objects.create(name="Security Provider", slug="security-provider")
        self.endpoint = APIEndpoint.objects.create(provider=self.provider, name="Security Endpoint", base_url="https://security.example.com", api_key=self.raw_endpoint_key)
        self.customer = Customer.objects.create(name="Security Customer")
        self.credential = CustomerCredential.objects.create(customer=self.customer, provider=self.provider, endpoint=self.endpoint, api_key=self.raw_customer_key, start_date=date.today())

    def user(self, username, sensitive=False):
        user = User.objects.create_user(username=username, email=f"{username}@example.com", password="password", is_staff=True)
        permissions = Permission.objects.filter(codename__in=(
            "view_apiendpoint", "change_apiendpoint",
            "view_customercredential", "change_customercredential",
        ))
        user.user_permissions.add(*permissions)
        if sensitive:
            user.user_permissions.add(*Permission.objects.filter(codename="view_sensitive_api_key"))
        return user

    def test_unauthorized_admin_cannot_retrieve_keys(self):
        self.client.force_login(self.user("restricted"))
        for url in (
            f"/admin/providers/apiendpoint/{self.endpoint.pk}/change/",
            f"/admin/customer_credentials/customercredential/{self.credential.pk}/change/",
        ):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, self.raw_endpoint_key)
            self.assertNotContains(response, self.raw_customer_key)

    def test_authorized_admin_can_retrieve_keys_on_detail(self):
        self.client.force_login(self.user("authorized", sensitive=True))
        self.assertContains(self.client.get(f"/admin/providers/apiendpoint/{self.endpoint.pk}/change/"), self.raw_endpoint_key)
        self.assertContains(self.client.get(f"/admin/customer_credentials/customercredential/{self.credential.pk}/change/"), self.raw_customer_key)

    def test_list_pages_are_always_masked(self):
        self.client.force_login(self.user("list-authorized", sensitive=True))
        endpoint_response = self.client.get("/admin/providers/apiendpoint/")
        credential_response = self.client.get("/admin/customer_credentials/customercredential/")
        self.assertNotContains(endpoint_response, self.raw_endpoint_key)
        self.assertNotContains(credential_response, self.raw_customer_key)
        self.assertContains(endpoint_response, self.endpoint.masked_api_key)

    def test_audit_and_validation_never_include_keys(self):
        self.endpoint.api_key = "sk-endpoint-replacement"
        self.endpoint.save()
        log = AuditLog.objects.filter(model_name="APIEndpoint", action="UPDATE").latest("created_at")
        self.assertEqual(log.changed_fields["api_key"], {"old": "changed", "new": "changed"})
        serialized = f"{log.description}{log.changed_fields}"
        self.assertNotIn(self.raw_endpoint_key, serialized)
        self.assertNotIn("sk-endpoint-replacement", serialized)
        invalid = CustomerCredential(customer=self.customer, provider=self.provider, endpoint=self.endpoint, api_key=self.raw_customer_key, start_date=date.today(), expire_date=date(2000, 1, 1))
        with self.assertRaises(ValidationError) as error:
            invalid.full_clean()
        self.assertNotIn(self.raw_customer_key, str(error.exception))
