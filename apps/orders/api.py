from django.db.models import Q
from django.utils.translation import gettext as _
from django_ratelimit.core import is_ratelimited
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from apps.cart.services import get_cart, load_cart_with_items

from .models import Order, OrderStatus, PaymentMethod, Region
from .serializers import OrderCreateSerializer, OrderSerializer
from .services import EmptyCart, InsufficientStock, change_status, create_order


class OrderViewSet(viewsets.ViewSet):
    """Authenticated order endpoints.

    GET  /api/orders/  -> current user's orders
    POST /api/orders/  -> create an order from the cart (COD)
    """

    permission_classes = [IsAuthenticated]

    def list(self, request):
        orders = (
            Order.objects.filter(user=request.user)
            .select_related("region")
            .prefetch_related("items")
            .order_by("-created_at")
        )
        return Response(OrderSerializer(orders, many=True, context={"request": request}).data)

    def retrieve(self, request, pk=None):
        try:
            order = (
                Order.objects.select_related("region")
                .prefetch_related("items")
                .get(pk=pk, user=request.user)
            )
        except Order.DoesNotExist:
            return Response({"detail": _("Not found.")}, status=status.HTTP_404_NOT_FOUND)
        return Response(OrderSerializer(order, context={"request": request}).data)

    def create(self, request):
        # Rate limit: 10 orders/hour/user.
        if is_ratelimited(request, group="order-create", key="user", rate="10/h",
                          method="POST", increment=True):
            return Response(
                {"detail": _("Too many orders. Please try again later.")},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if data["payment_method"] == PaymentMethod.ONLINE:
            return Response(
                {"detail": _("Online payment is not available yet. Please choose Cash on Delivery.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart = load_cart_with_items(get_cart(request, create=False))
        if cart is None or not cart.items.all():
            return Response({"detail": _("Your cart is empty.")}, status=status.HTTP_400_BAD_REQUEST)
        region = Region.objects.get(pk=data["region_id"])
        try:
            order = create_order(
                user=request.user,
                receiver_name=data["receiver_name"],
                receiver_phone=data["receiver_phone"],
                region=region,
                address=data["address"],
                payment_method=PaymentMethod.COD,
                cart=cart,
            )
        except InsufficientStock as exc:
            return Response(
                {"detail": str(exc), "item": exc.item_name, "available": exc.available},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except EmptyCart:
            return Response({"detail": _("Your cart is empty.")}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"id": order.pk, **OrderSerializer(order, context={"request": request}).data},
            status=status.HTTP_201_CREATED,
        )


class AdminOrderViewSet(viewsets.ViewSet):
    """Admin-only order management (IsAdminUser)."""

    permission_classes = [IsAdminUser]

    def _get_order(self, pk):
        return (
            Order.objects.select_related("region")
            .prefetch_related("items")
            .get(pk=pk)
        )

    def list(self, request):
        qs = Order.objects.select_related("region").prefetch_related("items").order_by("-created_at")
        status_filter = request.query_params.get("status")
        if status_filter in OrderStatus.values:
            qs = qs.filter(status=status_filter)
        q = request.query_params.get("q")
        if q:
            flt = Q(receiver_name__icontains=q) | Q(receiver_phone__icontains=q)
            if q.isdigit():
                flt |= Q(order_number=int(q))
            qs = qs.filter(flt)
        return Response(OrderSerializer(qs, many=True, context={"request": request}).data)

    @action(detail=True, methods=["patch"], url_path="status")
    def set_status(self, request, pk=None):
        try:
            order = self._get_order(pk)
        except Order.DoesNotExist:
            return Response({"detail": _("Not found.")}, status=status.HTTP_404_NOT_FOUND)
        new_status = request.data.get("status")
        if new_status not in OrderStatus.values:
            return Response({"detail": _("Invalid status.")}, status=status.HTTP_400_BAD_REQUEST)
        ok, error = change_status(order, new_status)
        if not ok:
            return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)
        order.refresh_from_db()
        return Response({
            "id": order.pk,
            "status": order.status,
            "status_display": order.get_status_display(),
        })

    @action(detail=True, methods=["get"], url_path="whatsapp-link")
    def whatsapp_link(self, request, pk=None):
        try:
            order = self._get_order(pk)
        except Order.DoesNotExist:
            return Response({"detail": _("Not found.")}, status=status.HTTP_404_NOT_FOUND)
        return Response({"url": order.whatsapp_url})
