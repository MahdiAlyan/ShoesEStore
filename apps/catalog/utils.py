from django.utils.translation import get_language


def localized(obj, base):
    """Return the active-language value of a dual `<base>_en`/`<base>_ar` field.

    Falls back to English when the active language is unavailable or empty.
    """
    lang = (get_language() or "en")[:2]
    value = getattr(obj, f"{base}_{lang}", None)
    return value or getattr(obj, f"{base}_en")
