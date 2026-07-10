import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

PHONE_RE = re.compile(r"^\+?[0-9]{7,15}$")


def normalize_phone(raw, default_country_code=None):
    """Normalize a receiver phone to `+<digits>`.

    - keeps a leading `+`;
    - if none, strips a single leading zero and prepends
      DEFAULT_PHONE_COUNTRY_CODE (ASSUMPTIONS A6/§20.2).
    """
    if raw is None:
        return ""
    raw = str(raw).strip()
    cc = default_country_code or getattr(settings, "DEFAULT_PHONE_COUNTRY_CODE", "+961")
    has_plus = raw.startswith("+")
    digits = re.sub(r"\D", "", raw)
    if has_plus:
        return "+" + digits
    if digits.startswith("0"):  # drop a single national trunk-prefix zero
        digits = digits[1:]
    cc_digits = re.sub(r"\D", "", cc)
    return "+" + cc_digits + digits


def validate_phone(value):
    if not PHONE_RE.match(value or ""):
        raise ValidationError(_("Enter a valid phone number (7–15 digits, optional +)."))


def wa_digits(phone):
    """Digits-only form for wa.me deep links (no +, no separators)."""
    return re.sub(r"\D", "", phone or "")
