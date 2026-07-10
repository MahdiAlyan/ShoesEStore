from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True,
        related_name="cart", verbose_name=_("user"),
    )
    session_key = models.CharField(_("session key"), max_length=40, null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("cart")
        verbose_name_plural = _("carts")

    def __str__(self):
        owner = self.user.email if self.user_id else f"session:{self.session_key}"
        return f"Cart({owner})"

    @property
    def subtotal(self):
        return sum((item.line_total for item in self.items.all()), Decimal("0.00"))

    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())

    def add(self, variant, quantity=1):
        """Add `quantity` of a variant, capped at available stock.

        Returns (item, error) — error is a lazy string when the request was
        clamped/rejected because it exceeded stock, else None.
        """
        quantity = max(1, int(quantity))
        item, _created = self.items.get_or_create(variant=variant, defaults={"quantity": 0})
        desired = item.quantity + quantity
        if desired > variant.stock:
            item.quantity = variant.stock
            item.save()
            return item, _("Only %(n)d left in stock.") % {"n": variant.stock}
        item.quantity = desired
        item.save()
        return item, None

    def set_quantity(self, item, quantity):
        quantity = int(quantity)
        if quantity <= 0:
            item.delete()
            return None, None
        if quantity > item.variant.stock:
            item.quantity = item.variant.stock
            item.save()
            return item, _("Only %(n)d left in stock.") % {"n": item.variant.stock}
        item.quantity = quantity
        item.save()
        return item, None

    def merge_from(self, other):
        """Merge another cart's items into this one, summing and capping at stock."""
        if other is None or other.pk == self.pk:
            return
        for other_item in other.items.select_related("variant").all():
            self.add(other_item.variant, other_item.quantity)
        other.items.all().delete()


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items", verbose_name=_("cart"))
    variant = models.ForeignKey(
        "catalog.ProductVariant", on_delete=models.CASCADE, related_name="cart_items", verbose_name=_("variant")
    )
    quantity = models.PositiveIntegerField(_("quantity"), default=1)

    class Meta:
        verbose_name = _("cart item")
        verbose_name_plural = _("cart items")
        unique_together = ("cart", "variant")

    def __str__(self):
        return f"{self.variant.sku} x{self.quantity}"

    @property
    def unit_price(self):
        return self.variant.price

    @property
    def line_total(self):
        return self.unit_price * self.quantity
