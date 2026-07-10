from decimal import Decimal

from django.db import transaction
from django.utils.translation import gettext as _

from apps.catalog.models import ProductVariant

from .models import Order, OrderItem, OrderStatus, PaymentMethod


class InsufficientStock(Exception):
    """Raised when a cart line exceeds available stock at order time."""

    def __init__(self, item_name, available):
        self.item_name = item_name
        self.available = available
        super().__init__(
            _("Not enough stock for %(name)s (only %(n)d left).")
            % {"name": item_name, "n": available}
        )


class EmptyCart(Exception):
    pass


@transaction.atomic
def create_order(*, user, receiver_name, receiver_phone, region, address,
                 payment_method, cart):
    """Create an order from a cart, decrementing stock atomically.

    Locks the affected variant rows (select_for_update), re-checks stock,
    decrements, snapshots line items, and clears the cart — all in one
    transaction. Raises InsufficientStock (naming the offending item) or
    EmptyCart.
    """
    cart_items = list(cart.items.select_related("variant__product", "variant__color", "variant__size"))
    if not cart_items:
        raise EmptyCart(_("Your cart is empty."))

    variant_ids = [ci.variant_id for ci in cart_items]
    # Lock the variant rows for the duration of the transaction.
    locked = {
        v.id: v
        for v in ProductVariant.objects.select_for_update()
        .select_related("product", "color", "size")
        .filter(id__in=variant_ids)
    }

    subtotal = Decimal("0.00")
    for ci in cart_items:
        variant = locked.get(ci.variant_id)
        if variant is None or ci.quantity > variant.stock:
            available = variant.stock if variant else 0
            # Canonical (English) snapshot names, matching OrderItem snapshots.
            name = f"{ci.variant.product.name_en} ({ci.variant.color.name_en}/{ci.variant.size.value})"
            raise InsufficientStock(name, available)
        subtotal += variant.price * ci.quantity

    delivery_fee = region.delivery_fee
    order = Order.objects.create(
        user=user,
        order_number=Order.next_order_number(),
        receiver_name=receiver_name,
        receiver_phone=receiver_phone,
        region=region,
        address=address,
        delivery_fee=delivery_fee,
        subtotal=subtotal,
        total=subtotal + delivery_fee,
        payment_method=payment_method or PaymentMethod.COD,
        status=OrderStatus.PENDING,
    )

    for ci in cart_items:
        variant = locked[ci.variant_id]
        OrderItem.objects.create(
            order=order,
            variant=variant,
            product_name=variant.product.name_en,
            color_name=variant.color.name_en,
            size_value=variant.size.value,
            unit_price=variant.price,
            quantity=ci.quantity,
        )
        variant.stock -= ci.quantity
        variant.save(update_fields=["stock"])

    cart.items.all().delete()
    return order


@transaction.atomic
def restock_order(order):
    """Return an order's items to stock (used when cancelling)."""
    items = order.items.select_related("variant").all()
    variant_ids = [it.variant_id for it in items]
    locked = {
        v.id: v
        for v in ProductVariant.objects.select_for_update().filter(id__in=variant_ids)
    }
    for it in items:
        variant = locked.get(it.variant_id)
        if variant:
            variant.stock += it.quantity
            variant.save(update_fields=["stock"])


@transaction.atomic
def change_status(order, new_status):
    """Apply a validated status transition; CANCELLED restocks.

    Returns (ok, error_message).
    """
    order = Order.objects.select_for_update().get(pk=order.pk)
    if not order.can_transition_to(new_status):
        return False, _("Invalid status change.")
    if new_status == OrderStatus.CANCELLED:
        restock_order(order)
    order.status = new_status
    order.save(update_fields=["status", "updated_at"])
    return True, None
