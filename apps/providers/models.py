"""Provider and upstream API endpoint models."""

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class Provider(TimeStampedModel):
    """An AI service provider such as OpenAI or Anthropic."""

    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ("name",)
        verbose_name = _("Provider")
        verbose_name_plural = _("Providers")

    def __str__(self) -> str:
        return self.name


class APIEndpoint(TimeStampedModel):
    """An owner-managed upstream API connection for a provider."""

    provider = models.ForeignKey(
        Provider,
        on_delete=models.PROTECT,
        related_name="endpoints",
    )
    name = models.CharField(max_length=200)
    base_url = models.URLField()
    api_key = models.TextField()
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ("provider__name", "name")
        verbose_name = _("API Endpoint")
        verbose_name_plural = _("API Endpoints")
        indexes = [models.Index(fields=("provider", "is_active"))]
        permissions = (("view_sensitive_api_key", "Can view sensitive API keys"),)

    def clean(self):
        super().clean()
        if not self.pk and not self.api_key:
            raise ValidationError(
                {"api_key": "An API key is required when creating an endpoint."}
            )

    def __str__(self) -> str:
        return f"{self.provider.name} - {self.name}"

    @property
    def masked_api_key(self) -> str:
        """Return a safe display value without exposing the complete key."""
        if not self.api_key:
            return "-"
        if len(self.api_key) <= 8:
            return "*" * len(self.api_key)
        return f"{self.api_key[:4]}{'*' * 12}{self.api_key[-4:]}"
