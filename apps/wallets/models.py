"""Cryptocurrency wallet inventory models."""

from django.db import models

from apps.core.models import TimeStampedModel


class Wallet(TimeStampedModel):
    """A cryptocurrency wallet owned or controlled by the operator."""

    name = models.CharField(max_length=200)
    currency = models.CharField(max_length=20, db_index=True)
    network = models.CharField(max_length=50, db_index=True)
    address = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "Wallet"
        verbose_name_plural = "Wallets"
        indexes = [
            models.Index(fields=("currency", "network", "is_active")),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def masked_address(self) -> str:
        """Return a shortened address for safe list-page display."""
        if len(self.address) <= 10:
            return self.address
        return f"{self.address[:6]}...{self.address[-4:]}"
