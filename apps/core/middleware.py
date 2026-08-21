"""Middleware supporting request-aware audit logging."""

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from apps.core.audit_context import reset_audit_user, set_audit_user


class AuditUserMiddleware:
    """Expose an authenticated staff user to model audit signals."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        user = getattr(request, "user", None)
        audit_user = user if getattr(user, "is_staff", False) else None
        token = set_audit_user(audit_user)
        try:
            return self.get_response(request)
        finally:
            reset_audit_user(token)
