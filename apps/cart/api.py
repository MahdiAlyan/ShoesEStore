from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.catalog.models import ProductVariant

from .models import CartItem
from .serializers import CartSerializer
from .services import get_cart, load_cart_with_items


class CartViewSet(viewsets.ViewSet):
    """Session- or user-scoped cart.

    GET    /api/cart/                -> cart contents + totals
    POST   /api/cart/items/          -> {variant_id, quantity} add
    PATCH  /api/cart/items/{id}/     -> {quantity} set
    DELETE /api/cart/items/{id}/     -> remove
    """

    permission_classes = [AllowAny]

    def _cart_response(self, request, extra_status=status.HTTP_200_OK, warning=None):
        cart = load_cart_with_items(get_cart(request))
        data = CartSerializer(cart, context={"request": request}).data
        if warning:
            data["warning"] = str(warning)
        return Response(data, status=extra_status)

    def list(self, request):
        return self._cart_response(request)

    @action(detail=False, methods=["post"], url_path="items")
    def add_item(self, request):
        variant_id = request.data.get("variant_id")
        quantity = request.data.get("quantity", 1)
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return Response({"detail": _("Invalid quantity.")}, status=status.HTTP_400_BAD_REQUEST)
        if quantity < 1:
            return Response({"detail": _("Quantity must be at least 1.")}, status=status.HTTP_400_BAD_REQUEST)

        variant = get_object_or_404(
            ProductVariant.objects.select_related("product"), pk=variant_id
        )
        if variant.stock < 1:
            return Response(
                {"detail": _("This item is out of stock.")}, status=status.HTTP_400_BAD_REQUEST
            )

        cart = get_cart(request)
        _item, warning = cart.add(variant, quantity)
        if warning:
            return self._cart_response(request, status.HTTP_400_BAD_REQUEST, warning)
        return self._cart_response(request, status.HTTP_201_CREATED)

    @action(detail=False, methods=["patch", "delete"], url_path=r"items/(?P<item_id>[0-9]+)")
    def item_detail(self, request, item_id=None):
        cart = get_cart(request)
        item = get_object_or_404(CartItem.objects.select_related("variant"), pk=item_id, cart=cart)

        if request.method == "DELETE":
            item.delete()
            return self._cart_response(request)

        quantity = request.data.get("quantity")
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return Response({"detail": _("Invalid quantity.")}, status=status.HTTP_400_BAD_REQUEST)
        _item, warning = cart.set_quantity(item, quantity)
        if warning:
            return self._cart_response(request, status.HTTP_400_BAD_REQUEST, warning)
        return self._cart_response(request)
