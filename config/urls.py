"""Root URL configuration for TokenLedger."""

from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from django.views.generic import RedirectView

from django.contrib import admin

urlpatterns = [
    path("", RedirectView.as_view(url="/admin/", permanent=False), name="root"),
    path(
        "accounts/profile/",
        RedirectView.as_view(url="/admin/", permanent=False),
        name="accounts-profile-redirect",
    ),
    path("i18n/", include("django.conf.urls.i18n")),
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
