from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class SignupForm(UserCreationForm):
    """Email + names + password signup. Email format validation only."""

    first_name = forms.CharField(
        label=_("First name"), max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control form-control-lg"}),
    )
    last_name = forms.CharField(
        label=_("Last name"), max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control form-control-lg"}),
    )
    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs={"class": "form-control form-control-lg", "autocomplete": "email"}),
    )

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs.update({"class": "form-control form-control-lg", "autocomplete": "new-password"})
        self.fields["password2"].widget.attrs.update({"class": "form-control form-control-lg", "autocomplete": "new-password"})

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("An account with this email already exists."))
        return email


class EmailLoginForm(AuthenticationForm):
    """Login by email. AuthenticationForm's `username` field carries the email."""

    username = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs={"class": "form-control form-control-lg", "autocomplete": "email", "autofocus": True}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password"].widget.attrs.update({"class": "form-control form-control-lg", "autocomplete": "current-password"})

    error_messages = {
        "invalid_login": _("Please enter a correct email and password."),
        "inactive": _("This account is inactive."),
    }
