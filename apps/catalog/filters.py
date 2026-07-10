from decimal import Decimal, InvalidOperation


def _decimal(value):
    try:
        return Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return None


def filter_products(queryset, params):
    """Apply ?category=&color=&size=&min_price=&max_price= to a Product queryset.

    `category` is a slug; `color` is a Color id; `size` is a Size id. Unknown or
    malformed values are ignored (no results narrowing on bad input).
    """
    category = params.get("category")
    if category:
        queryset = queryset.filter(category__slug=category)

    color = params.get("color")
    color = color if color and str(color).isdigit() else None
    size = params.get("size")
    size = size if size and str(size).isdigit() else None

    if color and size:
        # A SINGLE variant must match both color and size (one join), so a
        # product only matches if that exact color/size combination exists.
        queryset = queryset.filter(variants__color_id=color, variants__size_id=size)
    elif color:
        queryset = queryset.filter(variants__color_id=color)
    elif size:
        queryset = queryset.filter(variants__size_id=size)

    min_price = _decimal(params.get("min_price"))
    if min_price is not None:
        queryset = queryset.filter(base_price__gte=min_price)

    max_price = _decimal(params.get("max_price"))
    if max_price is not None:
        queryset = queryset.filter(base_price__lte=max_price)

    # color/size filters join through variants and can duplicate rows.
    return queryset.distinct()
