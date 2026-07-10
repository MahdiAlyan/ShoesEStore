from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.catalog.utils import localized

from .phone import validate_phone


class OrderStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending")
    CONFIRMED = "CONFIRMED", _("Confirmed")
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY", _("Out for delivery")
    DELIVERED = "DELIVERED", _("Delivered")
    CANCELLED = "CANCELLED", _("Cancelled")
    RETURNED = "RETURNED", _("Returned")


# Allowed forward transitions. CANCELLED restocks (handled in services).
STATUS_TRANSITIONS = {
    OrderStatus.PENDING: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.OUT_FOR_DELIVERY, OrderStatus.CANCELLED},
    OrderStatus.OUT_FOR_DELIVERY: {OrderStatus.DELIVERED, OrderStatus.CANCELLED},
    OrderStatus.DELIVERED: {OrderStatus.RETURNED},
    OrderStatus.CANCELLED: set(),
    OrderStatus.RETURNED: set(),
}


class PaymentMethod(models.TextChoices):
    COD = "COD", _("Cash on Delivery")
    ONLINE = "ONLINE", _("Online Payment")


class Region(models.Model):
    name_en = models.CharField(_("name (EN)"), max_length=120)
    name_ar = models.CharField(_("name (AR)"), max_length=120)
    delivery_fee = models.DecimalField(_("delivery fee (USD)"), max_digits=10, decimal_places=2)
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("region")
        verbose_name_plural = _("regions")
        ordering = ["name_en"]

    def __str__(self):
        return self.name_en

    @property
    def name(self):
        return localized(self, "name")


class Order(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders", verbose_name=_("user")
    )
    receiver_name = models.CharField(_("receiver name"), max_length=150)
    receiver_phone = models.CharField(_("receiver phone"), max_length=20, validators=[validate_phone])
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name="orders", verbose_name=_("region"))
    address = models.TextField(_("address"))
    delivery_fee = models.DecimalField(_("delivery fee"), max_digits=10, decimal_places=2, default=Decimal("0.00"))
    subtotal = models.DecimalField(_("subtotal"), max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(_("total"), max_digits=10, decimal_places=2, default=Decimal("0.00"))
    payment_method = models.CharField(
        _("payment method"), max_length=10, choices=PaymentMethod.choices, default=PaymentMethod.COD
    )
    status = models.CharField(
        _("status"), max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("order")
        verbose_name_plural = _("orders")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"Order #{self.pk}"

    def get_absolute_url(self):
        return reverse("orders:success", kwargs={"pk": self.pk})

    def can_transition_to(self, new_status):
        return new_status in STATUS_TRANSITIONS.get(self.status, set())

    @property
    def whatsapp_url(self):
        from .whatsapp import build_whatsapp_url
        return build_whatsapp_url(self)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items", verbose_name=_("order"))
    variant = models.ForeignKey(
        "catalog.ProductVariant", on_delete=models.PROTECT, related_name="order_items", verbose_name=_("variant")
    )
    # Snapshots so the receipt/WhatsApp text is stable even if the catalog changes.
    product_name = models.CharField(_("product name"), max_length=200)
    color_name = models.CharField(_("color"), max_length=60)
    size_value = models.CharField(_("size"), max_length=10)
    unit_price = models.DecimalField(_("unit price"), max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(_("quantity"))

    class Meta:
        verbose_name = _("order item")
        verbose_name_plural = _("order items")

    def __str__(self):
        return f"{self.product_name} x{self.quantity}"

    @property
    def line_total(self):
        return self.unit_price * self.quantity
