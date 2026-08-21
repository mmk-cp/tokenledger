"""Shared Unfold admin helpers and dashboard context."""

from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.http import HttpRequest
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm

from apps.core.forms import UserChangeForm, UserCreationForm
from apps.core.models import AuditLog, User


class BaseModelAdmin(ModelAdmin):
    """Base class for all TokenLedger model administration classes."""

    list_per_page = 50
    save_on_top = True
    warn_unsaved_form = True


if admin.site.is_registered(Group):
    admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(BaseUserAdmin, BaseModelAdmin):
    """Unfold-styled administration for the TokenLedger user model."""

    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
        "created_at",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("username",)
    readonly_fields = ("created_at", "updated_at", "last_login", "date_joined")
    fieldsets = (
        (None, {"fields": ("username", "password")} ),
        (
            "Personal Information",
            {"fields": ("first_name", "last_name", "email")},
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            "Important Dates",
            {"fields": ("last_login", "date_joined", "created_at", "updated_at")},
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "usable_password",
                    "password1",
                    "password2",
                ),
            },
        ),
    )


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, BaseModelAdmin):
    """Unfold-styled administration for Django's built-in group model."""

    list_display = ("name",)
    search_fields = ("name",)


@admin.register(AuditLog)
class AuditLogAdmin(BaseModelAdmin):
    """Read-only Unfold administration for audit records."""

    list_display = (
        "created_at",
        "action",
        "model_name",
        "object_id",
        "user",
        "ip_address",
    )
    list_filter = ("action", "model_name", "created_at")
    search_fields = (
        "action",
        "model_name",
        "object_id",
        "description",
        "user__username",
        "user__email",
    )
    readonly_fields = (
        "user",
        "action",
        "model_name",
        "object_id",
        "description",
        "created_at",
        "updated_at",
        "ip_address",
    )
    fieldsets = (
        (
            "Event",
            {"fields": ("action", "description", "created_at", "updated_at")},
        ),
        (
            "Context",
            {"fields": ("user", "model_name", "object_id", "ip_address")},
        ),
    )
    list_select_related = ("user",)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: AuditLog | None = None,
    ) -> bool:
        return False

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: AuditLog | None = None,
    ) -> bool:
        return False


def dashboard_callback(request: HttpRequest, context: dict) -> dict:
    """Add foundation-stage content to the Unfold dashboard context."""
    context.update(
        {
            "dashboard_title": "TokenLedger foundation is ready",
            "dashboard_description": (
                "User management and audit logging are ready. Provider, wallet, "
                "customer, credit, transaction, and billing modules will follow."
            ),
            "dashboard_modules": [
                "Providers",
                "Wallets",
                "Customers",
                "Credits",
                "Transactions",
                "Billing",
            ],
        }
    )
    return context
