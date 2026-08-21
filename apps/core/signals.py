"""Automatic audit logging for important TokenLedger models."""

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from apps.core.audit_context import get_audit_user
from apps.core.models import AuditLog
from apps.currencies.models import Currency, ExchangeRate
from apps.customer_credentials.models import CustomerCredential
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
    CustomerCredential,
)
DETAILED_MODELS = (
    APIEndpoint,
    CustomerCredential,
    CreditPurchase,
    CustomerCreditAllocation,
    Transaction,
    Wallet,
)
_ORIGINAL_VALUES = {}


def _serialize(value):
    if value is None:
        return None
    return str(value)


def _field_values(instance):
    return {
        field.name: getattr(instance, field.attname)
        for field in instance._meta.concrete_fields
        if field.name not in {"id", "created_at", "updated_at"}
    }


@receiver(pre_save, dispatch_uid="audit_capture_detailed_original")
def capture_detailed_original(sender, instance, **kwargs):
    if sender not in DETAILED_MODELS or not instance.pk:
        return
    try:
        original = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return
    _ORIGINAL_VALUES[id(instance)] = _field_values(original)


def _create_audit_log(instance: object, action: str, changed_fields=None) -> None:
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
        changed_fields=changed_fields or {},
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
@receiver(post_save, sender=CustomerCredential, dispatch_uid="audit_customer_credential_save")
def audit_model_save(sender, instance, created: bool, **kwargs) -> None:
    """Record CREATE and UPDATE events for tracked models."""
    changed = {}
    if not created and sender in DETAILED_MODELS:
        original = _ORIGINAL_VALUES.pop(id(instance), {})
        current = _field_values(instance)
        sensitive = {"api_key"}
        for name, old_value in original.items():
            if old_value != current.get(name):
                changed[name] = {"old": "changed", "new": "changed"} if name in sensitive else {
                    "old": _serialize(old_value), "new": _serialize(current.get(name))
                }
    _create_audit_log(instance, "CREATE" if created else "UPDATE", changed)


@receiver(post_save, sender=CreditPurchase, dispatch_uid="create_purchase_transaction")
def create_purchase_transaction(sender, instance, created: bool, **kwargs) -> None:
    """Record the cash outflow represented by a newly created purchase."""
    if not created:
        return
    Transaction.objects.create(
        transaction_type=Transaction.TransactionType.PURCHASE,
        direction=Transaction.Direction.OUT,
        wallet=instance.wallet,
        amount=instance.paid_amount,
        currency=instance.paid_currency,
        transaction_date=instance.purchase_date,
        reference=f"Credit purchase {instance.pk}: {instance.name}",
        credit_purchase=instance,
    )


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
@receiver(post_delete, sender=CustomerCredential, dispatch_uid="audit_customer_credential_delete")
def audit_model_delete(sender, instance, **kwargs) -> None:
    """Record DELETE events for tracked models."""
    _create_audit_log(instance, "DELETE")
