from django import forms

from apps.customer_credentials.models import CustomerCredential


class CustomerCredentialAdminForm(forms.ModelForm):
    api_key = forms.CharField(required=False, strip=False, widget=forms.PasswordInput(render_value=True), help_text="Required when creating a credential. Leave blank to keep the current key.")

    class Meta:
        model = CustomerCredential
        fields = "__all__"

    def clean_api_key(self):
        value = self.cleaned_data.get("api_key")
        if value:
            return value
        if self.instance.pk:
            return type(self.instance).objects.only("api_key").get(pk=self.instance.pk).api_key
        raise forms.ValidationError("An API key is required when creating a credential.")
