"""Aggregated DRF router mounted under /api/."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.cart.api import CartViewSet
from apps.catalog.api import ProductViewSet
from apps.orders.api import AdminOrderViewSet, OrderViewSet

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")
router.register("cart", CartViewSet, basename="cart")
router.register("orders", OrderViewSet, basename="order")
router.register("admin/orders", AdminOrderViewSet, basename="admin-order")

urlpatterns = [
    path("", include(router.urls)),
]
