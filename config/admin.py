"""Unfold administration site configuration."""

from unfold.sites import UnfoldAdminSite


class TokenLedgerAdminSite(UnfoldAdminSite):
    """Project-wide administration site powered by Django Unfold."""

    site_title = "TokenLedger Administration"
    site_header = "TokenLedger"
    index_title = "Operations dashboard"

