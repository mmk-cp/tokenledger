"""Customer record models."""

from django.db import models

from apps.core.models import TimeStampedModel


class Customer(TimeStampedModel):
    """A customer managed by the TokenLedger operator."""

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"
        SUSPENDED = "SUSPENDED", "Suspended"

    name = models.CharField(max_length=200)
    company_name = models.CharField(max_length=200, blank=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    telegram = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Customer"
        verbose_name_plural = "Customers"

    def __str__(self) -> str:
        return self.name
