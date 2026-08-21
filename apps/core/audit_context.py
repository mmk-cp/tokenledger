"""Request-local context used by audit signal handlers."""

from contextvars import ContextVar, Token

from django.contrib.auth.models import AnonymousUser

_current_user: ContextVar[object | None] = ContextVar(
    "tokenledger_audit_user",
    default=None,
)


def set_audit_user(user: object | None) -> Token:
    """Store an authenticated admin user for the current request context."""
    if isinstance(user, AnonymousUser) or not getattr(user, "is_authenticated", False):
        user = None
    return _current_user.set(user)


def reset_audit_user(token: Token) -> None:
    """Restore the previous request-local audit user."""
    _current_user.reset(token)


def get_audit_user() -> object | None:
    """Return the user associated with the current admin request, if any."""
    return _current_user.get()
