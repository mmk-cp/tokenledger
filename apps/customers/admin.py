"""Unfold admin registration for customers."""

from django.contrib import admin

from apps.core.admin import BaseModelAdmin
from apps.customers.models import Customer


@admin.register(Customer)
class CustomerAdmin(BaseModelAdmin):
    """Unfold administration for customer records."""

    list_display = ("name", "company_name", "email", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("name", "company_name", "email", "phone", "telegram")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "Customer",
            {"fields": ("name", "company_name", "status")},
        ),
        (
            "Contact Information",
            {"fields": ("email", "phone", "telegram")},
        ),
        ("Internal Notes", {"fields": ("notes",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
