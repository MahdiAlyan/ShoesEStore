from django.shortcuts import render

from .services import get_cart, load_cart_with_items


def cart_detail(request):
    cart = load_cart_with_items(get_cart(request, create=False))
    items = list(cart.items.all()) if cart else []
    return render(request, "cart/detail.html", {"cart": cart, "items": items})
