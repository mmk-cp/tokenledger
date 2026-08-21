"""Cryptocurrency wallet inventory models."""

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel
from apps.currencies.models import Currency


class Wallet(TimeStampedModel):
    """A cryptocurrency wallet owned or controlled by the operator."""

    name = models.CharField(max_length=200)
    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name="wallets",
    )
    network = models.CharField(max_length=50, db_index=True)
    address = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ("name",)
        verbose_name = _("Wallet")
        verbose_name_plural = _("Wallets")
        indexes = [
            models.Index(
                fields=("currency", "network", "is_active"),
                name="wallets_wal_currenc_8bcacf_idx",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def masked_address(self) -> str:
        """Return a shortened address for safe list-page display."""
        if len(self.address) <= 10:
            return self.address
        return f"{self.address[:6]}...{self.address[-4:]}"
