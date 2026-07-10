"""Cart resolution + merge-on-login. Kept out of models to avoid import cycles."""
from django.db.models import Prefetch

from .models import Cart, CartItem

SESSION_CART_KEY = "cart_id"


def load_cart_with_items(cart):
    """Reload a cart with its items + variant graph prefetched (no N+1).

    Priming the cart's own `items` cache means the serializer and the
    `subtotal`/`item_count` model properties reuse it.
    """
    if cart is None:
        return None
    item_qs = CartItem.objects.select_related(
        "variant__product", "variant__color", "variant__size"
    ).prefetch_related("variant__product__images")
    return Cart.objects.prefetch_related(
        Prefetch("items", queryset=item_qs)
    ).get(pk=cart.pk)


def get_cart(request, create=True):
    """Return the active cart for the request (user- or session-scoped).

    Anonymous carts are tracked via `request.session['cart_id']` so the link
    survives Django's session-key rotation at login (which powers merge-on-login).
    """
    if request.user.is_authenticated:
        if not create:
            return getattr(request.user, "cart", None)
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return cart

    cart_id = request.session.get(SESSION_CART_KEY)
    cart = None
    if cart_id:
        cart = Cart.objects.filter(pk=cart_id, user__isnull=True).first()
    if cart is None and create:
        if not request.session.session_key:
            request.session.create()
        cart = Cart.objects.create(session_key=request.session.session_key)
        request.session[SESSION_CART_KEY] = cart.pk
    return cart


def merge_session_cart_on_login(sender, request, user, **kwargs):
    """user_logged_in receiver: fold the anonymous cart into the user's cart."""
    anon_id = request.session.get(SESSION_CART_KEY)
    if not anon_id:
        return
    anon = Cart.objects.filter(pk=anon_id, user__isnull=True).first()
    user_cart, _ = Cart.objects.get_or_create(user=user)
    if anon and anon.pk != user_cart.pk:
        user_cart.merge_from(anon)
        anon.delete()
    request.session[SESSION_CART_KEY] = user_cart.pk
