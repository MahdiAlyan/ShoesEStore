from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from .filters import filter_products
from .models import Category, Color, Product, Size

PRODUCTS_PER_PAGE = 12


def home(request):
    featured = (
        Product.objects.filter(is_active=True)
        .select_related("category")
        .prefetch_related("images", "variants")
        .order_by("-created_at")[:8]
    )
    return render(request, "catalog/home.html", {"featured_products": featured})


def product_list(request):
    qs = (
        Product.objects.filter(is_active=True)
        .select_related("category")
        .prefetch_related("images", "variants")
    )
    qs = filter_products(qs, request.GET)

    paginator = Paginator(qs, PRODUCTS_PER_PAGE)
    page = paginator.get_page(request.GET.get("page"))

    # Preserve active filters across pagination links.
    querydict = request.GET.copy()
    querydict.pop("page", None)
    filter_qs = querydict.urlencode()

    context = {
        "page_obj": page,
        "products": page.object_list,
        "categories": Category.objects.all(),
        "colors": Color.objects.all(),
        "sizes": Size.objects.all(),
        "filter_qs": filter_qs,
        "active": {
            "category": request.GET.get("category", ""),
            "color": request.GET.get("color", ""),
            "size": request.GET.get("size", ""),
            "min_price": request.GET.get("min_price", ""),
            "max_price": request.GET.get("max_price", ""),
        },
    }
    return render(request, "catalog/product_list.html", context)


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.filter(is_active=True)
        .select_related("category")
        .prefetch_related("images__color", "variants__color", "variants__size"),
        slug=slug,
    )
    variants = list(product.variants.all())
    colors = []
    seen_colors = set()
    for v in variants:
        if v.color_id not in seen_colors:
            seen_colors.add(v.color_id)
            colors.append(v.color)
    sizes = sorted({v.size for v in variants}, key=lambda s: (s.sort_order, s.value))

    # Availability map: {(color_id, size_id): stock} for the JS picker.
    availability = {f"{v.color_id}_{v.size_id}": v.stock for v in variants}
    variant_ids = {f"{v.color_id}_{v.size_id}": v.id for v in variants}

    context = {
        "product": product,
        "images": list(product.images.all()),
        "colors": colors,
        "sizes": sizes,
        "availability": availability,
        "variant_ids": variant_ids,
    }
    return render(request, "catalog/product_detail.html", context)


def handler404(request, exception=None):
    return render(request, "404.html", status=404)


def handler500(request):
    return render(request, "500.html", status=500)
