from django.contrib import admin

from .models import Category, Color, Product, ProductImage, ProductVariant, Size


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name_en", "category", "base_price", "is_active", "total_stock", "created_at")
    list_filter = ("is_active", "category")
    search_fields = ("name_en", "name_ar", "slug")
    prepopulated_fields = {"slug": ("name_en",)}
    inlines = [ProductImageInline, ProductVariantInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name_en", "name_ar", "slug")
    prepopulated_fields = {"slug": ("name_en",)}


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ("name_en", "name_ar", "hex_code")


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ("value", "sort_order")


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("sku", "product", "color", "size", "stock")
    list_filter = ("color", "size")
    search_fields = ("sku", "product__name_en")
