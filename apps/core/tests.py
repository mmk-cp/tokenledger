"""Tests for automatic audit logging."""

from datetime import date
from decimal import Decimal

from django.test import RequestFactory, TestCase

from apps.core.admin import dashboard_callback
from apps.core.models import AuditLog, User
from apps.credits.models import CreditBalance, CreditPurchase, CustomerCreditAllocation
from apps.customers.models import Customer
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
        self.assertEqual(metrics["Money Received"], "75.00")
        self.assertEqual(metrics["Money Spent"], "25.00")
        self.assertEqual(metrics["Net Cash Flow"], "50.00")
        self.assertEqual(metrics["Estimated Profit (USD)"], "20.00")
        self.assertEqual(len(context["recent_transactions"]), 2)
