"""Tests for automatic audit logging."""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib import admin
from django.test import RequestFactory, TestCase

from apps.core.admin import dashboard_callback
from apps.core.models import AuditLog, User
from apps.currencies.models import Currency, ExchangeRate
from apps.credits.models import CreditBalance, CreditPurchase, CustomerCreditAllocation
from apps.customers.models import Customer
from apps.customers.admin import CustomerAdmin
from apps.credits.admin import CustomerCreditAllocationAdmin
from apps.providers.models import Provider
from apps.providers.models import APIEndpoint
from apps.customer_credentials.models import CustomerCredential
from apps.transactions.models import Transaction
from apps.wallets.models import Wallet


class AuditSignalTests(TestCase):
    def test_creating_customer_creates_audit_log(self):
        customer = Customer.objects.create(name="Ali")

        log = AuditLog.objects.get(model_name="Customer", object_id=customer.pk)
        self.assertEqual(log.action, "CREATE")
        self.assertEqual(log.description, 'Created customer "Ali"')
        self.assertIsNone(log.user)

    def test_updating_wallet_creates_update_audit_log(self):
        wallet = Wallet.objects.create(
            name="Main Wallet",
            currency=Currency.objects.get(code="USDT"),
            network="TRC20",
            address="audit-test-wallet-address",
        )
        wallet.description = "Updated description"
        wallet.save()

        self.assertTrue(
            AuditLog.objects.filter(
                action="UPDATE",
                model_name="Wallet",
                object_id=wallet.pk,
            ).exists()
        )

    def test_deleting_transaction_creates_delete_audit_log(self):
        transaction = Transaction.objects.create(
            transaction_type=Transaction.TransactionType.EXPENSE,
            direction=Transaction.Direction.OUT,
            amount=Decimal("10.00"),
            currency=Currency.objects.get(code="USD"),
            transaction_date=date.today(),
        )
        object_id = str(transaction.pk)
        transaction.delete()

        self.assertTrue(
            AuditLog.objects.filter(
                action="DELETE",
                model_name="Transaction",
                object_id=object_id,
            ).exists()
        )

    def test_audit_log_does_not_audit_itself(self):
        initial_count = AuditLog.objects.count()
        AuditLog.objects.create(
            action="MANUAL",
            model_name="Test",
            object_id="1",
        )

        self.assertEqual(AuditLog.objects.count(), initial_count + 1)

    def test_wallet_update_captures_field_changes(self):
        wallet = Wallet.objects.create(name="Before", currency=Currency.objects.get(code="USDT"), network="TRC20", address="audit-change-wallet")
        wallet.name = "After"
        wallet.save()
        log = AuditLog.objects.filter(model_name="Wallet", action="UPDATE").latest("created_at")
        self.assertEqual(log.changed_fields["name"], {"old": "Before", "new": "After"})

    def test_credential_key_change_is_redacted(self):
        provider = Provider.objects.create(name="Secure Provider", slug="secure-provider")
        endpoint = APIEndpoint.objects.create(provider=provider, name="Secure", base_url="https://secure.example.com", api_key="endpoint-secret")
        customer = Customer.objects.create(name="Secure Customer")
        credential = CustomerCredential.objects.create(customer=customer, provider=provider, endpoint=endpoint, api_key="old-secret", start_date=date.today())
        credential.api_key = "new-secret"
        credential.save()
        log = AuditLog.objects.filter(model_name="CustomerCredential", action="UPDATE").latest("created_at")
        self.assertEqual(log.changed_fields["api_key"], {"old": "changed", "new": "changed"})
        self.assertNotIn("old-secret", str(log.changed_fields))
        self.assertNotIn("new-secret", str(log.changed_fields))


class DashboardTests(TestCase):
    def test_dashboard_calculations_for_staff_user(self):
        user = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="test-password",
            is_staff=True,
        )
        provider = Provider.objects.create(name="Provider", slug="provider")
        wallet = Wallet.objects.create(
            name="Dashboard Wallet",
            currency=Currency.objects.get(code="USD"),
            network="Internal",
            address="dashboard-test-wallet-address",
        )
        purchase = CreditPurchase.objects.create(
            provider=provider,
            wallet=wallet,
            name="Active Purchase",
            credit_amount_usd=Decimal("100.00"),
            paid_amount=Decimal("100.00"),
            paid_currency=Currency.objects.get(code="USD"),
            exchange_rate=Decimal("1.00"),
        )
        customer = Customer.objects.create(name="Dashboard Customer")
        CustomerCreditAllocation.objects.create(
            customer=customer,
            credit_purchase=purchase,
            allocated_credit_usd=Decimal("40.00"),
            cost_price_usd=Decimal("30.00"),
            selling_price_usd=Decimal("50.00"),
        )
        Transaction.objects.create(
            transaction_type=Transaction.TransactionType.CUSTOMER_PAYMENT,
            direction=Transaction.Direction.IN,
            amount=Decimal("75.00"),
            currency=Currency.objects.get(code="USD"),
            transaction_date=date.today(),
        )
        Transaction.objects.create(
            transaction_type=Transaction.TransactionType.EXPENSE,
            direction=Transaction.Direction.OUT,
            amount=Decimal("25.00"),
            currency=Currency.objects.get(code="USD"),
            transaction_date=date.today(),
        )
        request = RequestFactory().get("/admin/")
        request.user = user

        context = dashboard_callback(request, {})
        metrics = {
            item["label"]: item["value"] for item in context["dashboard_metrics"]
        }

        self.assertEqual(metrics["Purchased Credit (USD)"], "100.00")
        self.assertEqual(metrics["Allocated Credit (USD)"], "40.00")
        self.assertEqual(metrics["Remaining Available Credit (USD)"], "60.00")
        self.assertEqual(metrics["Total Customer Credit Value (USD)"], "40.00")
        self.assertEqual(metrics["Total Available Credit (USD)"], "60.00")
        self.assertEqual(metrics["Total Cost Basis (USD)"], "30.00")
        self.assertEqual(metrics["Total Purchased Cost (USD)"], "100.00")
        self.assertEqual(metrics["Total Credit Purchased (USD)"], "100.00")
        self.assertEqual(metrics["Average Purchase Cost"], "1.000000")
        self.assertEqual(metrics["Money Received (USD)"], "75.00")
        self.assertEqual(metrics["Money Spent (USD)"], "125.00")
        self.assertEqual(metrics["Net Cash Flow (USD)"], "-50.00")
        self.assertEqual(metrics["Estimated Profit (USD)"], "20.00")
        self.assertEqual(context["financial_report"]["revenue"], Decimal("75.00"))
        self.assertEqual(context["financial_report"]["costs"], Decimal("125.00"))
        self.assertEqual(context["financial_report"]["total_selling_value"], Decimal("50.00"))
        self.assertEqual(context["financial_report"]["estimated_profit"], Decimal("20.00"))
        self.assertEqual(context["top_customers_allocated"][0]["name"], "Dashboard Customer")
        self.assertEqual(context["top_customers_allocated"][0]["value"], Decimal("40.00"))
        self.assertEqual(context["top_customers_profit"][0]["value"], Decimal("20.00"))
        self.assertEqual(len(context["recent_transactions"]), 3)

    def test_dashboard_converts_multiple_currencies_and_skips_missing_rates(self):
        user = User.objects.create_user(
            username="currency-admin",
            email="currency-admin@example.com",
            password="test-password",
            is_staff=True,
        )
        conversion_date = date(2026, 8, 21)
        ExchangeRate.objects.create(
            base_currency=Currency.objects.get(code="USDT"),
            target_currency=Currency.objects.get(code="USD"),
            rate=Decimal("1.00"),
            effective_date=date(2026, 8, 1),
        )
        ExchangeRate.objects.create(
            base_currency=Currency.objects.get(code="EUR"),
            target_currency=Currency.objects.get(code="USD"),
            rate=Decimal("1.20"),
            effective_date=date(2026, 8, 1),
        )
        Transaction.objects.create(
            transaction_type=Transaction.TransactionType.CUSTOMER_PAYMENT,
            direction=Transaction.Direction.IN,
            amount=Decimal("100.00"),
            currency=Currency.objects.get(code="USDT"),
            transaction_date=conversion_date,
        )
        Transaction.objects.create(
            transaction_type=Transaction.TransactionType.CUSTOMER_PAYMENT,
            direction=Transaction.Direction.IN,
            amount=Decimal("50.00"),
            currency=Currency.objects.get(code="EUR"),
            transaction_date=conversion_date,
        )
        Transaction.objects.create(
            transaction_type=Transaction.TransactionType.CUSTOMER_PAYMENT,
            direction=Transaction.Direction.IN,
            amount=Decimal("10.00"),
            currency=Currency.objects.get(code="BTC"),
            transaction_date=conversion_date,
        )
        Transaction.objects.create(
            transaction_type=Transaction.TransactionType.EXPENSE,
            direction=Transaction.Direction.OUT,
            amount=Decimal("25.00"),
            currency=Currency.objects.get(code="USDT"),
            transaction_date=conversion_date,
        )
        request = RequestFactory().get("/admin/")
        request.user = user

        context = dashboard_callback(request, {})
        metrics = {
            item["label"]: item["value"] for item in context["dashboard_metrics"]
        }

        self.assertEqual(metrics["Money Received (USD)"], "160.00")
        self.assertEqual(metrics["Money Spent (USD)"], "25.00")
        self.assertEqual(metrics["Net Cash Flow (USD)"], "135.00")

    def test_dashboard_prefers_usd_snapshot_over_live_conversion(self):
        user = User.objects.create_user(
            username="snapshot-admin",
            email="snapshot-admin@example.com",
            password="test-password",
            is_staff=True,
        )
        usdt = Currency.objects.get(code="USDT")
        usd = Currency.objects.get(code="USD")
        transaction = Transaction.objects.create(
            transaction_type=Transaction.TransactionType.CUSTOMER_PAYMENT,
            direction=Transaction.Direction.IN,
            amount=Decimal("100.00"),
            currency=usdt,
            converted_amount=Decimal("125.00"),
            converted_currency=usd,
            conversion_rate=Decimal("1.25"),
            conversion_date=date.today(),
            transaction_date=date.today(),
        )
        request = RequestFactory().get("/admin/")
        request.user = user
        context = dashboard_callback(request, {})
        metrics = {item["label"]: item["value"] for item in context["dashboard_metrics"]}
        self.assertEqual(metrics["Money Received (USD)"], "125.00")
        transaction.delete()

    def test_dashboard_purchase_cost_prefers_snapshot_and_falls_back(self):
        user = User.objects.create_user(
            username="purchase-dashboard-admin",
            email="purchase-dashboard@example.com",
            password="test-password",
            is_staff=True,
        )
        usd = Currency.objects.get(code="USD")
        usdt = Currency.objects.get(code="USDT")
        eur = Currency.objects.get(code="EUR")
        provider = Provider.objects.create(name="Cost Provider", slug="cost-provider")
        wallet = Wallet.objects.create(
            name="Cost Wallet",
            currency=usdt,
            network="Internal",
            address="dashboard-purchase-cost-wallet",
        )
        valuation_date = date(2026, 8, 21)
        ExchangeRate.objects.create(
            base_currency=eur,
            target_currency=usd,
            rate=Decimal("1.20"),
            effective_date=date(2026, 8, 1),
        )
        CreditPurchase.objects.create(
            provider=provider,
            wallet=wallet,
            name="Snapshot Cost",
            credit_amount_usd=Decimal("200.00"),
            paid_amount=Decimal("100.00"),
            paid_currency=usdt,
            exchange_rate=Decimal("1.00"),
            converted_amount=Decimal("150.00"),
            converted_currency=usd,
            conversion_rate=Decimal("1.50"),
            conversion_date=valuation_date,
            purchase_date=valuation_date,
        )
        CreditPurchase.objects.create(
            provider=provider,
            wallet=wallet,
            name="Fallback Cost",
            credit_amount_usd=Decimal("100.00"),
            paid_amount=Decimal("50.00"),
            paid_currency=eur,
            exchange_rate=Decimal("1.20"),
            purchase_date=valuation_date,
        )
        CreditPurchase.objects.create(
            provider=provider,
            wallet=wallet,
            name="Missing Rate Cost",
            credit_amount_usd=Decimal("50.00"),
            paid_amount=Decimal("1.00"),
            paid_currency=Currency.objects.get(code="BTC"),
            exchange_rate=Decimal("1.00"),
            purchase_date=valuation_date,
        )
        request = RequestFactory().get("/admin/")
        request.user = user

        context = dashboard_callback(request, {})
        metrics = {item["label"]: item["value"] for item in context["dashboard_metrics"]}

        self.assertEqual(metrics["Total Purchased Cost (USD)"], "210.00")
        self.assertEqual(metrics["Total Credit Purchased (USD)"], "350.00")
        self.assertEqual(metrics["Average Purchase Cost"], "0.600000")


class CustomerAdminTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(name="Admin Customer")
        self.provider = Provider.objects.create(name="Admin Provider", slug="admin-provider")
        self.wallet = Wallet.objects.create(
            name="Admin Wallet",
            currency=Currency.objects.get(code="USD"),
            network="Internal",
            address="customer-admin-wallet-address",
        )
        purchase = CreditPurchase.objects.create(
            provider=self.provider,
            wallet=self.wallet,
            name="Admin Purchase",
            credit_amount_usd=Decimal("200.00"),
            paid_amount=Decimal("200.00"),
            paid_currency=Currency.objects.get(code="USD"),
            exchange_rate=Decimal("1.00"),
        )
        CustomerCreditAllocation.objects.create(
            customer=self.customer,
            credit_purchase=purchase,
            allocated_credit_usd=Decimal("80.00"),
            cost_price_usd=Decimal("60.00"),
            selling_price_usd=Decimal("100.00"),
        )
        CustomerCreditAllocation.objects.create(
            customer=self.customer,
            credit_purchase=purchase,
            allocated_credit_usd=Decimal("20.00"),
            cost_price_usd=Decimal("15.00"),
            selling_price_usd=Decimal("25.00"),
            status=CustomerCreditAllocation.Status.CANCELLED,
        )

    def test_customer_admin_annotations_and_detail_summaries(self):
        admin_instance = CustomerAdmin(Customer, admin.site)
        request = RequestFactory().get("/admin/customers/customer/")
        request.user = User(is_staff=True, is_active=True)
        customer = admin_instance.get_queryset(request).get(pk=self.customer.pk)

        self.assertEqual(customer.admin_total_allocated, Decimal("100.00"))
        self.assertEqual(customer.admin_remaining_credit, Decimal("80.00"))
        self.assertIn("Active allocations: 1", admin_instance.credit_summary(customer))

        Transaction.objects.create(
            customer=self.customer,
            transaction_type=Transaction.TransactionType.CUSTOMER_PAYMENT,
            direction=Transaction.Direction.IN,
            amount=Decimal("100.00"),
            currency=Currency.objects.get(code="USD"),
            transaction_date=date.today(),
        )
        Transaction.objects.create(
            customer=self.customer,
            transaction_type=Transaction.TransactionType.REFUND,
            direction=Transaction.Direction.OUT,
            amount=Decimal("20.00"),
            currency=Currency.objects.get(code="USD"),
            transaction_date=date.today(),
        )
        financial = admin_instance.financial_summary(self.customer)
        self.assertIn("Payments received: 100.00", financial)
        self.assertIn("Refunds: 20.00", financial)
        self.assertIn("Net paid: 80.00", financial)

    def test_customer_expiration_annotations(self):
        expected_expiration = date.today() + timedelta(days=10)
        CustomerCreditAllocation.objects.filter(
            customer=self.customer,
            status=CustomerCreditAllocation.Status.ACTIVE,
        ).update(expire_date=expected_expiration)
        admin_instance = CustomerAdmin(Customer, admin.site)
        request = RequestFactory().get("/admin/customers/customer/")
        request.user = User(is_staff=True, is_active=True)
        customer = admin_instance.get_queryset(request).get(pk=self.customer.pk)
        self.assertEqual(customer.admin_active_allocations, 1)
        self.assertEqual(customer.admin_next_expiration, expected_expiration)

    def test_dashboard_expiration_sections_and_allocation_days(self):
        today = date.today()
        active = CustomerCreditAllocation.objects.filter(
            customer=self.customer,
            status=CustomerCreditAllocation.Status.ACTIVE,
        ).first()
        active.expire_date = today + timedelta(days=5)
        active.save()
        expired = CustomerCreditAllocation.objects.filter(
            customer=self.customer,
            status=CustomerCreditAllocation.Status.CANCELLED,
        ).first()
        expired.status = CustomerCreditAllocation.Status.ACTIVE
        CustomerCreditAllocation.objects.filter(pk=expired.pk).update(
            status=CustomerCreditAllocation.Status.ACTIVE,
            expire_date=today - timedelta(days=2),
        )
        expired.refresh_from_db()
        no_date = CustomerCreditAllocation.objects.create(
            customer=self.customer,
            credit_purchase=active.credit_purchase,
            allocated_credit_usd=Decimal("5.00"),
            cost_price_usd=Decimal("4.00"),
            selling_price_usd=Decimal("6.00"),
        )

        user = User.objects.create_user(
            username="expiration-admin",
            email="expiration-admin@example.com",
            password="test-password",
            is_staff=True,
        )
        request = RequestFactory().get("/admin/")
        request.user = user
        context = dashboard_callback(request, {})
        self.assertEqual(list(context["expiring_credits"]), [active])
        self.assertEqual(list(context["expired_credits"]), [expired])

        allocation_admin = CustomerCreditAllocationAdmin(
            CustomerCreditAllocation, admin.site
        )
        queryset = allocation_admin.get_queryset(request)
        self.assertEqual(queryset.get(pk=active.pk).admin_days_until_expiration, 5)
        self.assertIsNone(queryset.get(pk=no_date.pk).admin_days_until_expiration)

    def test_credit_allocation_add_form_profit_display_handles_blank_object(self):
        allocation_admin = CustomerCreditAllocationAdmin(
            CustomerCreditAllocation, admin.site
        )
        blank_allocation = CustomerCreditAllocation()

        self.assertEqual(
            allocation_admin.profit_usd_display(blank_allocation),
            "-",
        )
