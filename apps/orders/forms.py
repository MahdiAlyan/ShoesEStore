from django import forms
from django.utils.translation import gettext_lazy as _

from .models import PaymentMethod, Region
from .phone import normalize_phone, validate_phone


class CheckoutForm(forms.Form):
    receiver_name = forms.CharField(
        label=_("Receiver name"), max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "name"}),
    )
    receiver_phone = forms.CharField(
        label=_("Receiver phone"), max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control", "inputmode": "tel", "placeholder": "+9613xxxxxx"}),
        help_text=_("We will contact you on WhatsApp to confirm."),
    )
    region = forms.ModelChoiceField(
        label=_("Delivery region"), queryset=Region.objects.filter(is_active=True),
        widget=forms.Select(attrs={"class": "form-select", "id": "id_region"}),
        empty_label=_("Select a region"),
    )
    address = forms.CharField(
        label=_("Delivery address"),
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3, "autocomplete": "street-address"}),
    )
    payment_method = forms.ChoiceField(
        label=_("Payment method"), choices=PaymentMethod.choices,
        initial=PaymentMethod.COD, widget=forms.RadioSelect,
    )

    def clean_receiver_phone(self):
        raw = self.cleaned_data["receiver_phone"]
        normalized = normalize_phone(raw)
        validate_phone(normalized)
        return normalized
