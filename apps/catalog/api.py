from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .filters import filter_products
from .models import Product
from .serializers import (
    ProductDetailSerializer,
    ProductListSerializer,
    VariantSerializer,
)


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """Public, read-only product catalog.

    list supports ?category=&color=&size=&min_price=&max_price=.
    """

    permission_classes = [AllowAny]
    lookup_field = "slug"

    def get_queryset(self):
        qs = (
            Product.objects.filter(is_active=True)
            .select_related("category")
            .prefetch_related("images", "variants__color", "variants__size")
        )
        if self.action == "list":
            qs = filter_products(qs, self.request.query_params)
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return ProductListSerializer
        return ProductDetailSerializer

    @action(detail=True, methods=["get"])
    def variants(self, request, slug=None):
        """Variant matrix with per-variant stock (drives the size/color picker)."""
        product = self.get_object()
        variants = product.variants.select_related("color", "size").all()
        data = VariantSerializer(variants, many=True, context={"request": request}).data
        return Response(data)
