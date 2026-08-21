"""Tests for automatic audit logging."""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from apps.core.models import AuditLog
from apps.customers.models import Customer
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
