import re

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response

from .filters import filter_products
from .models import Color, Product, ProductVariant, Size
from .serializers import (
    ProductDetailSerializer,
    ProductListSerializer,
    VariantSerializer,
)


def _sku_part(value):
    """Uppercased, hyphen-safe SKU fragment from a color/size string."""
    cleaned = re.sub(r"[^0-9A-Za-z]+", "-", str(value)).strip("-")
    return cleaned.upper()


def _unique_sku(base):
    """Return `base`, or `base-2`, `base-3`, … so the SKU stays globally unique."""
    sku = base
    n = 2
    while ProductVariant.objects.filter(sku=sku).exists():
        sku = f"{base}-{n}"
        n += 1
    return sku


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


class AdminProductViewSet(viewsets.ViewSet):
    """Admin-only product operations (IsAdminUser). Looked up by pk."""

    permission_classes = [IsAdminUser]

    @action(detail=True, methods=["post"], url_path="variants/bulk")
    def bulk_variants(self, request, pk=None):
        """Create every color×size combination that does not already exist (M6.3).

        Body: {color_ids, size_ids, stock, sku_prefix}. Existing combos are
        skipped silently. SKUs are ``{prefix or slug}-{color}-{size}`` uppercased
        and made globally unique. Returns {created, skipped}.
        """
        product = get_object_or_404(Product, pk=pk)
        color_ids = request.data.get("color_ids") or []
        size_ids = request.data.get("size_ids") or []
        prefix = (request.data.get("sku_prefix") or "").strip()

        try:
            stock = int(request.data.get("stock", 0))
            if stock < 0:
                raise ValueError
        except (TypeError, ValueError):
            return Response({"detail": _("Stock must be a non-negative whole number.")},
                            status=status.HTTP_400_BAD_REQUEST)

        colors = list(Color.objects.filter(id__in=color_ids))
        sizes = list(Size.objects.filter(id__in=size_ids))
        if not colors or not sizes:
            return Response({"detail": _("Select at least one color and one size.")},
                            status=status.HTTP_400_BAD_REQUEST)

        base = _sku_part(prefix) if prefix else _sku_part(product.slug)
        created = skipped = 0
        with transaction.atomic():
            existing = set(product.variants.values_list("color_id", "size_id"))
            for color in colors:
                for size in sizes:
                    if (color.id, size.id) in existing:
                        skipped += 1
                        continue
                    sku = _unique_sku(f"{base}-{_sku_part(color.name_en)}-{_sku_part(size.value)}")
                    ProductVariant.objects.create(
                        product=product, color=color, size=size, sku=sku, stock=stock,
                    )
                    existing.add((color.id, size.id))
                    created += 1

        return Response({"created": created, "skipped": skipped},
                        status=status.HTTP_201_CREATED)
