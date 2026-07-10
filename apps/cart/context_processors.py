from .services import get_cart


def cart_summary(request):
    """Cart item-count badge for the navbar (no cart is created just to read it)."""
    try:
        cart = get_cart(request, create=False)
    except Exception:
        cart = None
    return {"cart_count": cart.item_count if cart else 0}
