"""Automatic audit logging for important TokenLedger models."""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.core.audit_context import get_audit_user
from apps.core.models import AuditLog
from apps.currencies.models import Currency, ExchangeRate
from apps.credits.models import CreditPurchase, CustomerCreditAllocation
from apps.customers.models import Customer
from apps.providers.models import APIEndpoint, Provider
from apps.transactions.models import ExpenseCategory, Transaction
from apps.wallets.models import Wallet

TRACKED_MODELS = (
    Provider,
    APIEndpoint,
    Wallet,
    CreditPurchase,
    CustomerCreditAllocation,
    Customer,
    Transaction,
    ExpenseCategory,
    ExchangeRate,
    Currency,
)


def _create_audit_log(instance: object, action: str) -> None:
    """Create a concise audit event without storing field-level snapshots."""
    model_name = instance._meta.object_name
    action_label = {"CREATE": "Created", "UPDATE": "Updated", "DELETE": "Deleted"}[
        action
    ]
    AuditLog.objects.create(
        user=get_audit_user(),
        action=action,
        model_name=model_name,
        object_id=str(instance.pk),
        description=f'{action_label} {instance._meta.verbose_name.lower()} "{instance}"',
    )


@receiver(post_save, sender=Provider, dispatch_uid="audit_provider_save")
@receiver(post_save, sender=APIEndpoint, dispatch_uid="audit_api_endpoint_save")
@receiver(post_save, sender=Wallet, dispatch_uid="audit_wallet_save")
@receiver(post_save, sender=CreditPurchase, dispatch_uid="audit_credit_purchase_save")
@receiver(
    post_save,
    sender=CustomerCreditAllocation,
    dispatch_uid="audit_customer_credit_allocation_save",
)
@receiver(post_save, sender=Customer, dispatch_uid="audit_customer_save")
@receiver(post_save, sender=Transaction, dispatch_uid="audit_transaction_save")
@receiver(post_save, sender=ExpenseCategory, dispatch_uid="audit_expense_category_save")
@receiver(post_save, sender=ExchangeRate, dispatch_uid="audit_exchange_rate_save")
@receiver(post_save, sender=Currency, dispatch_uid="audit_currency_save")
def audit_model_save(sender, instance, created: bool, **kwargs) -> None:
    """Record CREATE and UPDATE events for tracked models."""
    _create_audit_log(instance, "CREATE" if created else "UPDATE")


@receiver(post_delete, sender=Provider, dispatch_uid="audit_provider_delete")
@receiver(post_delete, sender=APIEndpoint, dispatch_uid="audit_api_endpoint_delete")
@receiver(post_delete, sender=Wallet, dispatch_uid="audit_wallet_delete")
@receiver(post_delete, sender=CreditPurchase, dispatch_uid="audit_credit_purchase_delete")
@receiver(
    post_delete,
    sender=CustomerCreditAllocation,
    dispatch_uid="audit_customer_credit_allocation_delete",
)
@receiver(post_delete, sender=Customer, dispatch_uid="audit_customer_delete")
@receiver(post_delete, sender=Transaction, dispatch_uid="audit_transaction_delete")
@receiver(post_delete, sender=ExpenseCategory, dispatch_uid="audit_expense_category_delete")
@receiver(post_delete, sender=ExchangeRate, dispatch_uid="audit_exchange_rate_delete")
@receiver(post_delete, sender=Currency, dispatch_uid="audit_currency_delete")
def audit_model_delete(sender, instance, **kwargs) -> None:
    """Record DELETE events for tracked models."""
    _create_audit_log(instance, "DELETE")
