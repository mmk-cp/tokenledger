"""Forms for managing provider connections in the Unfold admin."""

from django import forms
from django.utils.translation import gettext_lazy as _
from unfold.widgets import UnfoldAdminPasswordWidget

from apps.providers.models import APIEndpoint


class APIEndpointAdminForm(forms.ModelForm):
    """Keep existing keys out of rendered forms while allowing replacement."""

    api_key = forms.CharField(
        label=_("API key"),
        required=False,
        strip=False,
        widget=UnfoldAdminPasswordWidget(render_value=False),
        help_text=_("Required when creating an endpoint. Leave blank to keep the current key."),
    )

    class Meta:
        model = APIEndpoint
        fields = "__all__"

    def clean_api_key(self):
        value = self.cleaned_data.get("api_key")
        if value:
            return value
        if self.instance.pk:
            return type(self.instance).objects.only("api_key").get(pk=self.instance.pk).api_key
        raise forms.ValidationError(_("An API key is required when creating an endpoint."))
