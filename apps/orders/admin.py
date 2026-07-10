from django.contrib import admin

from .models import Order, OrderItem, Region


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("variant", "product_name", "color_name", "size_value", "unit_price", "quantity")


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("name_en", "name_ar", "delivery_fee", "is_active")
    list_filter = ("is_active",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "receiver_name", "receiver_phone", "status", "payment_method", "total", "created_at")
    list_filter = ("status", "payment_method", "region")
    search_fields = ("id", "receiver_name", "receiver_phone")
    readonly_fields = ("subtotal", "total", "delivery_fee", "created_at", "updated_at")
    inlines = [OrderItemInline]
