"""Cloudflare Turnstile: render flags + server-side verification.

Active ONLY when settings.TURNSTILE_ENABLED is true. When disabled (or on any
error / missing keys) verification is skipped/soft so the app never crashes and
forms keep working with no widget.
"""
import json
import logging
from urllib import error, parse, request

from django.conf import settings

logger = logging.getLogger(__name__)


def turnstile_context(_request):
    """Expose flags to every template (registered as a context processor)."""
    return {
        "TURNSTILE_ENABLED": getattr(settings, "TURNSTILE_ENABLED", False),
        "TURNSTILE_SITE_KEY": getattr(settings, "TURNSTILE_SITE_KEY", ""),
    }


def verify_turnstile(req):
    """Return True if the Turnstile token verifies (or if Turnstile is off)."""
    if not getattr(settings, "TURNSTILE_ENABLED", False):
        return True
    secret = getattr(settings, "TURNSTILE_SECRET_KEY", "")
    token = req.POST.get("cf-turnstile-response", "")
    if not secret or not token:
        return False
    payload = parse.urlencode({
        "secret": secret,
        "response": token,
        "remoteip": req.META.get("REMOTE_ADDR", ""),
    }).encode()
    try:
        with request.urlopen(settings.TURNSTILE_VERIFY_URL, data=payload, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        return bool(data.get("success"))
    except (error.URLError, ValueError, TimeoutError) as exc:  # network/parse errors
        logger.warning("Turnstile verification failed: %s", exc)
        return False
