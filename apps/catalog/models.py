from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .utils import localized
from .validators import validate_image_size


class Category(models.Model):
    name_en = models.CharField(_("name (EN)"), max_length=120)
    name_ar = models.CharField(_("name (AR)"), max_length=120)
    slug = models.SlugField(_("slug"), max_length=140, unique=True)

    class Meta:
        verbose_name = _("category")
        verbose_name_plural = _("categories")
        ordering = ["name_en"]

    def __str__(self):
        return self.name_en

    @property
    def name(self):
        return localized(self, "name")


class Color(models.Model):
    name_en = models.CharField(_("name (EN)"), max_length=60)
    name_ar = models.CharField(_("name (AR)"), max_length=60)
    hex_code = models.CharField(_("hex code"), max_length=7, default="#000000")

    class Meta:
        verbose_name = _("color")
        verbose_name_plural = _("colors")
        ordering = ["name_en"]

    def __str__(self):
        return self.name_en

    @property
    def name(self):
        return localized(self, "name")


class Size(models.Model):
    value = models.CharField(_("value"), max_length=10)  # "40", "41.5"
    sort_order = models.PositiveIntegerField(_("sort order"), default=0)

    class Meta:
        verbose_name = _("size")
        verbose_name_plural = _("sizes")
        ordering = ["sort_order", "value"]

    def __str__(self):
        return self.value


class Product(models.Model):
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products", verbose_name=_("category")
    )
    name_en = models.CharField(_("name (EN)"), max_length=200)
    name_ar = models.CharField(_("name (AR)"), max_length=200)
    slug = models.SlugField(_("slug"), max_length=220, unique=True)
    description_en = models.TextField(_("description (EN)"), blank=True)
    description_ar = models.TextField(_("description (AR)"), blank=True)
    base_price = models.DecimalField(_("base price (USD)"), max_digits=10, decimal_places=2)
    is_active = models.BooleanField(_("active"), default=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("product")
        verbose_name_plural = _("products")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active", "-created_at"]),
        ]

    def __str__(self):
        return self.name_en

    @property
    def name(self):
        return localized(self, "name")

    @property
    def description(self):
        return localized(self, "description")

    def get_absolute_url(self):
        return reverse("catalog:product_detail", kwargs={"slug": self.slug})

    @property
    def main_image(self):
        img = next((i for i in self.images.all() if i.is_main), None)
        if img is None:
            img = next(iter(self.images.all()), None)
        return img

    @property
    def total_stock(self):
        return sum(v.stock for v in self.variants.all())

    @property
    def in_stock(self):
        return self.total_stock > 0


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images", verbose_name=_("product")
    )
    color = models.ForeignKey(
        Color, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="images", verbose_name=_("color"),
    )
    image = models.ImageField(_("image"), upload_to="products/", validators=[validate_image_size])
    is_main = models.BooleanField(_("main image"), default=False)

    class Meta:
        verbose_name = _("product image")
        verbose_name_plural = _("product images")
        ordering = ["-is_main", "id"]

    def __str__(self):
        return f"{self.product.name_en} image #{self.pk}"


class ProductVariant(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="variants", verbose_name=_("product")
    )
    color = models.ForeignKey(Color, on_delete=models.PROTECT, related_name="variants", verbose_name=_("color"))
    size = models.ForeignKey(Size, on_delete=models.PROTECT, related_name="variants", verbose_name=_("size"))
    sku = models.CharField(_("SKU"), max_length=60, unique=True)
    stock = models.PositiveIntegerField(_("stock"), default=0)

    class Meta:
        verbose_name = _("variant")
        verbose_name_plural = _("variants")
        unique_together = ("product", "color", "size")
        ordering = ["size__sort_order", "color__name_en"]

    def __str__(self):
        return f"{self.sku}"

    @property
    def price(self):
        # MVP: variants share the product base price (ASSUMPTIONS §20.7).
        return self.product.base_price

    @property
    def in_stock(self):
        return self.stock > 0

    @property
    def label(self):
        return f"{self.product.name} · {self.color.name} · {self.size.value}"
