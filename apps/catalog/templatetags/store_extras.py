"""Storefront/dashboard template helpers."""
from django import template
from django.urls import translate_url

from apps.catalog.money import format_money

register = template.Library()


@register.filter(name="money")
def money(value):
    """Render a price as canonical ``$X.YY`` (dot-decimal) in any language."""
    return format_money(value)


@register.simple_tag(takes_context=True)
def switch_lang_url(context, lang_code):
    """Current page URL rewritten for ``lang_code`` (M1.1 language switcher).

    Rendered while the *page's* language is active, so ``translate_url`` can
    resolve the prefixed path (e.g. ``/ar/products/``) and reverse it under the
    target language (``/products/``). Passing this already-translated path as
    ``next`` fixes the AR→EN switch, which otherwise kept the ``/ar/`` prefix.
    """
    request = context.get("request")
    path = request.get_full_path() if request is not None else "/"
    return translate_url(path, lang_code)
