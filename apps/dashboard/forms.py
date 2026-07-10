from django import forms
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _

from apps.catalog.models import Category, Product, ProductImage, ProductVariant
from apps.orders.models import Region

_TEXT = {"class": "form-control"}
_SELECT = {"class": "form-select"}
_CHECK = {"class": "form-check-input"}


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["category", "name_en", "name_ar", "slug", "description_en",
                  "description_ar", "base_price", "is_active"]
        widgets = {
            "category": forms.Select(attrs=_SELECT),
            "name_en": forms.TextInput(attrs=_TEXT),
            "name_ar": forms.TextInput(attrs=_TEXT),
            "slug": forms.TextInput(attrs=_TEXT),
            "description_en": forms.Textarea(attrs={**_TEXT, "rows": 3}),
            "description_ar": forms.Textarea(attrs={**_TEXT, "rows": 3}),
            "base_price": forms.NumberInput(attrs={**_TEXT, "step": "0.01", "min": "0"}),
            "is_active": forms.CheckboxInput(attrs=_CHECK),
        }


VariantFormSet = inlineformset_factory(
    Product, ProductVariant,
    fields=["color", "size", "sku", "stock"], extra=1, can_delete=True,
    widgets={
        "color": forms.Select(attrs=_SELECT),
        "size": forms.Select(attrs=_SELECT),
        "sku": forms.TextInput(attrs=_TEXT),
        "stock": forms.NumberInput(attrs={**_TEXT, "min": "0"}),
    },
)

ImageFormSet = inlineformset_factory(
    Product, ProductImage,
    fields=["image", "color", "is_main"], extra=1, can_delete=True,
    widgets={
        "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
        "color": forms.Select(attrs=_SELECT),
        "is_main": forms.CheckboxInput(attrs=_CHECK),
    },
)


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name_en", "name_ar", "slug"]
        widgets = {
            "name_en": forms.TextInput(attrs=_TEXT),
            "name_ar": forms.TextInput(attrs=_TEXT),
            "slug": forms.TextInput(attrs=_TEXT),
        }


class RegionForm(forms.ModelForm):
    class Meta:
        model = Region
        fields = ["name_en", "name_ar", "delivery_fee", "is_active"]
        widgets = {
            "name_en": forms.TextInput(attrs=_TEXT),
            "name_ar": forms.TextInput(attrs=_TEXT),
            "delivery_fee": forms.NumberInput(attrs={**_TEXT, "step": "0.01", "min": "0"}),
            "is_active": forms.CheckboxInput(attrs=_CHECK),
        }
