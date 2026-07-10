from rest_framework import serializers

from .models import CartItem


class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="variant.product.name", read_only=True)
    product_slug = serializers.CharField(source="variant.product.slug", read_only=True)
    color_name = serializers.CharField(source="variant.color.name", read_only=True)
    size_value = serializers.CharField(source="variant.size.value", read_only=True)
    sku = serializers.CharField(source="variant.sku", read_only=True)
    stock = serializers.IntegerField(source="variant.stock", read_only=True)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    line_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    image = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            "id", "variant", "product_name", "product_slug", "color_name",
            "size_value", "sku", "stock", "quantity", "unit_price", "line_total", "image",
        ]

    def get_image(self, obj):
        img = obj.variant.product.main_image
        if not img:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(img.image.url) if request else img.image.url


class CartSerializer(serializers.Serializer):
    items = CartItemSerializer(many=True, read_only=True)
    item_count = serializers.IntegerField(read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
