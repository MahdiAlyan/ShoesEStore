from urllib.parse import quote

from .phone import wa_digits


def build_whatsapp_message(order):
    """Build the exact bilingual confirmation message (spec §8).

    Item/region snapshots are taken from the order so the text is stable.
    """
    lines = [
        f"Hello {order.receiver_name}! \U0001F44B",
        f"Order #{order.pk} — ShoeStore",
    ]
    for item in order.items.all():
        lines.append(
            f"- {item.product_name} | {item.color_name} | Size {item.size_value} "
            f"x{item.quantity} — ${item.line_total:.2f}"
        )
    lines.append(f"Delivery ({order.region.name}): ${order.delivery_fee:.2f}")
    lines.append(f"Total: ${order.total:.2f}")
    lines.append("Please reply to CONFIRM your order.")
    lines.append("الرجاء الرد لتأكيد الطلب.")
    return "\n".join(lines)


def build_whatsapp_url(order):
    """`https://wa.me/<digits>?text=<urlencoded bilingual message>`."""
    text = build_whatsapp_message(order)
    return f"https://wa.me/{wa_digits(order.receiver_phone)}?text={quote(text)}"
