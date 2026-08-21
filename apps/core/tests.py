"""Tests for automatic audit logging."""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib import admin
from django.test import RequestFactory, TestCase

from apps.core.admin import dashboard_callback
from apps.core.models import AuditLog, User
from apps.currencies.models import ExchangeRate
from apps.credits.models import CreditBalance, CreditPurchase, CustomerCreditAllocation
from apps.customers.models import Customer
from apps.customers.admin import CustomerAdmin
from apps.credits.admin import CustomerCreditAllocationAdmin
from apps.providers.models import Provider
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
            currency="USDT",
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
            currency="USD",
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
            currency="USD",
            network="Internal",
            address="dashboard-test-wallet-address",
        )
        purchase = CreditPurchase.objects.create(
            provider=provider,
            wallet=wallet,
            name="Active Purchase",
            credit_amount_usd=Decimal("100.00"),
            paid_amount=Decimal("100.00"),
            paid_currency="USD",
            exchange_rate=Decimal("1.00"),
        )
        CreditBalance.objects.create(
            purchase=purchase,
            used_credit_usd=Decimal("0.00"),
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
            currency="USD",
            transaction_date=date.today(),
        )
        Transaction.objects.create(
            transaction_type=Transaction.TransactionType.EXPENSE,
            direction=Transaction.Direction.OUT,
            amount=Decimal("25.00"),
            currency="USD",
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
        self.assertEqual(metrics["Total Available Credit (USD)"], "100.00")
        self.assertEqual(metrics["Total Cost Basis (USD)"], "30.00")
        self.assertEqual(metrics["Money Received (USD)"], "75.00")
        self.assertEqual(metrics["Money Spent (USD)"], "25.00")
        self.assertEqual(metrics["Net Cash Flow (USD)"], "50.00")
        self.assertEqual(metrics["Estimated Profit (USD)"], "20.00")
        self.assertEqual(len(context["recent_transactions"]), 2)

    def test_dashboard_converts_multiple_currencies_and_skips_missing_rates(self):
        user = User.objects.create_user(
            username="currency-admin",
            email="currency-admin@example.com",
            password="test-password",
            is_staff=True,
        )
        conversion_date = date(2026, 8, 21)
        ExchangeRate.objects.create(
            base_currency="USDT",
            target_currency="USD",
            rate=Decimal("1.00"),
            effective_date=date(2026, 8, 1),
        )
        ExchangeRate.objects.create(
            base_currency="EUR",
            target_currency="USD",
            rate=Decimal("1.20"),
            effective_date=date(2026, 8, 1),
        )
        Transaction.objects.create(
            transaction_type=Transaction.TransactionType.CUSTOMER_PAYMENT,
            direction=Transaction.Direction.IN,
            amount=Decimal("100.00"),
            currency="USDT",
            transaction_date=conversion_date,
        )
        Transaction.objects.create(
            transaction_type=Transaction.TransactionType.CUSTOMER_PAYMENT,
            direction=Transaction.Direction.IN,
            amount=Decimal("50.00"),
            currency="EUR",
            transaction_date=conversion_date,
        )
        Transaction.objects.create(
            transaction_type=Transaction.TransactionType.CUSTOMER_PAYMENT,
            direction=Transaction.Direction.IN,
            amount=Decimal("10.00"),
            currency="BTC",
            transaction_date=conversion_date,
        )
        Transaction.objects.create(
            transaction_type=Transaction.TransactionType.EXPENSE,
            direction=Transaction.Direction.OUT,
            amount=Decimal("25.00"),
            currency="USDT",
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


class CustomerAdminTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(name="Admin Customer")
        self.provider = Provider.objects.create(name="Admin Provider", slug="admin-provider")
        self.wallet = Wallet.objects.create(
            name="Admin Wallet",
            currency="USD",
            network="Internal",
            address="customer-admin-wallet-address",
        )
        purchase = CreditPurchase.objects.create(
            provider=self.provider,
            wallet=self.wallet,
            name="Admin Purchase",
            credit_amount_usd=Decimal("200.00"),
            paid_amount=Decimal("200.00"),
            paid_currency="USD",
            exchange_rate=Decimal("1.00"),
        )
        CreditBalance.objects.create(purchase=purchase, used_credit_usd=Decimal("0"))
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
            currency="USD",
            transaction_date=date.today(),
        )
        Transaction.objects.create(
            customer=self.customer,
            transaction_type=Transaction.TransactionType.REFUND,
            direction=Transaction.Direction.OUT,
            amount=Decimal("20.00"),
            currency="USD",
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
