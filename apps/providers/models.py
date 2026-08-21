"""Provider and upstream API endpoint models."""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import models

from apps.core.models import TimeStampedModel


class EncryptedTextField(models.TextField):
    """Encrypt text values before they are written to the database."""

    _prefix = "enc:"

    @staticmethod
    def _fernet() -> Fernet:
        configured_key = getattr(settings, "API_KEY_ENCRYPTION_KEY", "")
        source = configured_key or getattr(settings, "SECRET_KEY", "")
        if not source:
            raise ImproperlyConfigured(
                "API_KEY_ENCRYPTION_KEY or SECRET_KEY must be configured."
            )
        try:
            return Fernet(source.encode())
        except (ValueError, TypeError):
            derived_key = base64.urlsafe_b64encode(
                hashlib.sha256(source.encode()).digest()
            )
            return Fernet(derived_key)

    @classmethod
    def _decrypt(cls, value: str) -> str:
        if not value or not value.startswith(cls._prefix):
            return value
        try:
            return cls._fernet().decrypt(value[len(cls._prefix) :].encode()).decode()
        except InvalidToken as exc:
            raise ImproperlyConfigured(
                "API key could not be decrypted. Check API_KEY_ENCRYPTION_KEY."
            ) from exc

    def from_db_value(self, value, expression, connection):
        return self._decrypt(value) if value is not None else None

    def to_python(self, value):
        if value is None:
            return value
        if isinstance(value, bytes):
            value = value.decode()
        if not isinstance(value, str) or not value.startswith(self._prefix):
            return value
        return self._decrypt(value)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if not value or value.startswith(self._prefix):
            return value
        encrypted = self._fernet().encrypt(value.encode()).decode()
        return f"{self._prefix}{encrypted}"


class Provider(TimeStampedModel):
    """An AI service provider such as OpenAI or Anthropic."""

    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "Provider"
        verbose_name_plural = "Providers"

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
    api_key = EncryptedTextField()
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ("provider__name", "name")
        verbose_name = "API Endpoint"
        verbose_name_plural = "API Endpoints"
        indexes = [models.Index(fields=("provider", "is_active"))]

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
