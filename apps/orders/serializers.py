from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .models import Order, OrderItem, PaymentMethod, Region
from .phone import normalize_phone, validate_phone


class OrderItemSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "product_name", "color_name", "size_value", "unit_price", "quantity", "line_total"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    region_name = serializers.CharField(source="region.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "status", "status_display", "payment_method", "receiver_name",
            "receiver_phone", "region_name", "address", "delivery_fee", "subtotal",
            "total", "created_at", "items",
        ]


class OrderCreateSerializer(serializers.Serializer):
    receiver_name = serializers.CharField(max_length=150)
    receiver_phone = serializers.CharField(max_length=20)
    region_id = serializers.IntegerField()
    address = serializers.CharField()
    payment_method = serializers.ChoiceField(
        choices=PaymentMethod.choices, default=PaymentMethod.COD
    )

    def validate_receiver_phone(self, value):
        normalized = normalize_phone(value)
        validate_phone(normalized)
        return normalized

    def validate_region_id(self, value):
        if not Region.objects.filter(pk=value, is_active=True).exists():
            raise serializers.ValidationError(_("Invalid region."))
        return value
