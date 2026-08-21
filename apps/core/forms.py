"""Unfold-compatible forms for the TokenLedger user model."""

from unfold.forms import UserChangeForm as UnfoldUserChangeForm
from unfold.forms import UserCreationForm as UnfoldUserCreationForm

from apps.core.models import User


class UserCreationForm(UnfoldUserCreationForm):
    """Create a TokenLedger user with the Unfold form widgets."""

    class Meta(UnfoldUserCreationForm.Meta):
        model = User
        fields = ("username", "email")


class UserChangeForm(UnfoldUserChangeForm):
    """Edit a TokenLedger user with the Unfold form widgets."""

    class Meta(UnfoldUserChangeForm.Meta):
        model = User
        fields = "__all__"
