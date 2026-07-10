from urllib.parse import quote

from apps.catalog.money import format_money

from .phone import wa_digits


def build_whatsapp_message(order):
    """Build the exact bilingual confirmation message (spec §8).

    Item/region snapshots are taken from the order so the text is stable.
    Money is rendered via the canonical ``format_money`` helper (M1.3).
    """
    lines = [
        f"Hello {order.receiver_name}! \U0001F44B",
        f"Order #{order.order_number} — ShoeStore",
    ]
    for item in order.items.all():
        lines.append(
            f"- {item.product_name} | {item.color_name} | Size {item.size_value} "
            f"x{item.quantity} — {format_money(item.line_total)}"
        )
    lines.append(f"Delivery ({order.region.name}): {format_money(order.delivery_fee)}")
    lines.append(f"Total: {format_money(order.total)}")
    lines.append("Please reply to CONFIRM your order.")
    lines.append("الرجاء الرد لتأكيد الطلب.")
    return "\n".join(lines)


def build_whatsapp_url(order):
    """`https://wa.me/<digits>?text=<urlencoded bilingual message>`."""
    text = build_whatsapp_message(order)
    return f"https://wa.me/{wa_digits(order.receiver_phone)}?text={quote(text)}"
