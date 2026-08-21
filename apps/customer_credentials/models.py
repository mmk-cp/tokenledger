from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import TimeStampedModel
from apps.credits.models import CustomerCreditAllocation
from apps.customers.models import Customer
from apps.providers.models import APIEndpoint, EncryptedTextField, Provider


class CustomerCredential(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        EXPIRED = "EXPIRED", "Expired"
        CANCELLED = "CANCELLED", "Cancelled"

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="credentials")
    provider = models.ForeignKey(Provider, on_delete=models.PROTECT, related_name="customer_credentials")
    endpoint = models.ForeignKey(APIEndpoint, on_delete=models.PROTECT, related_name="customer_credentials")
    credit_allocation = models.ForeignKey(
        CustomerCreditAllocation,
        on_delete=models.PROTECT,
        related_name="customer_credentials",
        null=True,
        blank=True,
    )
    encrypted_api_key = EncryptedTextField(blank=True)
    assigned_credit_usd = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))])
    cost_price_usd = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))])
    selling_price_usd = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))])
    start_date = models.DateField()
    expire_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Customer Credential"
        verbose_name_plural = "Customer Credentials"
        indexes = [models.Index(fields=("provider", "status")), models.Index(fields=("expire_date", "status"))]
        permissions = (("view_sensitive_api_key", "Can view decrypted API keys"),)

    def clean(self):
        super().clean()
        errors = {}
        if self.endpoint_id and self.provider_id:
            owner = APIEndpoint.objects.filter(pk=self.endpoint_id).values_list("provider_id", flat=True).first()
            if owner != self.provider_id:
                errors["endpoint"] = "The endpoint must belong to the selected provider."
        if self.credit_allocation_id:
            allocation = self.credit_allocation
            if self.customer_id and allocation.customer_id != self.customer_id:
                errors["credit_allocation"] = "The allocation must belong to the selected customer."
            if self.provider_id and allocation.provider_id != self.provider_id:
                errors["credit_allocation"] = "The allocation must belong to the selected provider."
        if not self.pk and not self.encrypted_api_key:
            errors["encrypted_api_key"] = "An API key is required when creating a credential."
        if self.expire_date and self.start_date and self.expire_date < self.start_date:
            errors["expire_date"] = "Expiration date cannot be before start date."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.customer} - {self.provider} - {self.endpoint}"

    @property
    def masked_api_key(self):
        if not self.encrypted_api_key:
            return "-"
        if len(self.encrypted_api_key) <= 8:
            return "*" * len(self.encrypted_api_key)
        return f"{self.encrypted_api_key[:4]}{'*' * 12}{self.encrypted_api_key[-4:]}"
