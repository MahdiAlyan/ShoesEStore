from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from apps.common.turnstile import verify_turnstile

from .forms import EmailLoginForm, SignupForm

# Lazy so it is translated per-request, not frozen to English at import time.
RATE_MSG = gettext_lazy("Too many attempts. Please wait a minute and try again.")
TURNSTILE_MSG = gettext_lazy("Please complete the human verification.")


def _safe_next(request):
    """Return a safe same-origin ?next= redirect target, or the home page."""
    nxt = request.POST.get("next") or request.GET.get("next")
    if nxt and url_has_allowed_host_and_scheme(
        nxt, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return nxt
    return reverse("catalog:home")


@ratelimit(key="ip", rate="5/m", method="POST", block=False)
def signup(request):
    if request.user.is_authenticated:
        return redirect("catalog:home")

    limited = getattr(request, "limited", False)
    if request.method == "POST" and not limited:
        form = SignupForm(request.POST)
        if not verify_turnstile(request):
            messages.error(request, TURNSTILE_MSG)
            return render(request, "accounts/signup.html", {"form": form, "next": _next_value(request)})
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, _("Welcome to ShoeStore! Your account is ready."))
            return redirect(_safe_next(request))
    else:
        form = SignupForm()
        if limited:
            messages.error(request, RATE_MSG)

    return render(request, "accounts/signup.html", {"form": form, "next": _next_value(request)})


@ratelimit(key="ip", rate="5/m", method="POST", block=False)
def login_view(request):
    if request.user.is_authenticated:
        return redirect("catalog:home")

    limited = getattr(request, "limited", False)
    if request.method == "POST" and not limited:
        form = EmailLoginForm(request, data=request.POST)
        if not verify_turnstile(request):
            messages.error(request, TURNSTILE_MSG)
            return render(request, "accounts/login.html", {"form": form, "next": _next_value(request)})
        if form.is_valid():
            auth_login(request, form.get_user())
            messages.success(request, _("Signed in successfully."))
            return redirect(_safe_next(request))
    else:
        form = EmailLoginForm(request)
        if limited:
            messages.error(request, RATE_MSG)

    return render(request, "accounts/login.html", {"form": form, "next": _next_value(request)})


@require_POST
def logout_view(request):
    auth_logout(request)
    messages.info(request, _("You have been signed out."))
    return redirect("catalog:home")


def _next_value(request):
    return request.POST.get("next") or request.GET.get("next") or ""
