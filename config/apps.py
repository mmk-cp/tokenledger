"""Django application configuration for project infrastructure."""

from django.contrib.admin.apps import AdminConfig


class TokenLedgerAdminConfig(AdminConfig):
    """Use the TokenLedger Unfold site for Django admin autodiscovery."""

    default_site = "config.admin.TokenLedgerAdminSite"
