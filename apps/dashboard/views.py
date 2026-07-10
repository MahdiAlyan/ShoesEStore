from django.contrib import messages
from django.db import transaction
from django.db.models import Count, DecimalField, Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.catalog.models import Category, Product, ProductVariant
from apps.orders.models import Order, OrderStatus, Region

from .decorators import staff_required
from .forms import CategoryForm, ImageFormSet, ProductForm, RegionForm, VariantFormSet

LOW_STOCK = 5


@staff_required
def overview(request):
    today = timezone.localdate()
    revenue = Order.objects.filter(status=OrderStatus.DELIVERED).aggregate(
        total=Coalesce(Sum("total"), 0, output_field=DecimalField(max_digits=12, decimal_places=2))
    )["total"]
    context = {
        "active_nav": "overview",
        "orders_today": Order.objects.filter(created_at__date=today).count(),
        "pending_orders": Order.objects.filter(status=OrderStatus.PENDING).count(),
        "low_stock_count": ProductVariant.objects.filter(stock__lt=LOW_STOCK).count(),
        "low_stock_variants": ProductVariant.objects.filter(stock__lt=LOW_STOCK)
        .select_related("product", "color", "size")[:10],
        "revenue": revenue,
        "recent_orders": Order.objects.select_related("region").order_by("-created_at")[:8],
    }
    return render(request, "dashboard/overview.html", context)


# ---------- Products ----------
@staff_required
def products(request):
    qs = Product.objects.select_related("category").prefetch_related("variants").order_by("-created_at")
    return render(request, "dashboard/products_list.html", {"active_nav": "products", "products": qs})


@staff_required
def product_form(request, pk=None):
    product = get_object_or_404(Product, pk=pk) if pk else None
    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        variants = VariantFormSet(request.POST, instance=product, prefix="variants")
        images = ImageFormSet(request.POST, request.FILES, instance=product, prefix="images")
        # Validate everything BEFORE any write, then save atomically so an
        # invalid variant/image row can never leave an orphaned product.
        if form.is_valid() and variants.is_valid() and images.is_valid():
            with transaction.atomic():
                obj = form.save()
                variants.instance = obj
                images.instance = obj
                variants.save()
                images.save()
            messages.success(request, _("Product saved."))
            return redirect("dashboard:products")
    else:
        form = ProductForm(instance=product)
        variants = VariantFormSet(instance=product, prefix="variants")
        images = ImageFormSet(instance=product, prefix="images")

    return render(request, "dashboard/product_form.html", {
        "active_nav": "products", "form": form, "variants": variants,
        "images": images, "product": product,
    })


@staff_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        product.delete()
        messages.success(request, _("Product deleted."))
    return redirect("dashboard:products")


# ---------- Categories ----------
@staff_required
def categories(request):
    if request.method == "POST":
        pk = request.POST.get("id")
        instance = Category.objects.filter(pk=pk).first() if pk else None
        form = CategoryForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, _("Category saved."))
            return redirect("dashboard:categories")
    else:
        form = CategoryForm()
    return render(request, "dashboard/categories.html", {
        "active_nav": "categories", "form": form,
        "categories": Category.objects.annotate(n=Count("products")),
    })


@staff_required
def category_delete(request, pk):
    if request.method == "POST":
        try:
            Category.objects.get(pk=pk).delete()
            messages.success(request, _("Category deleted."))
        except Exception:
            messages.error(request, _("Cannot delete a category that still has products."))
    return redirect("dashboard:categories")


# ---------- Regions ----------
@staff_required
def regions(request):
    if request.method == "POST":
        pk = request.POST.get("id")
        instance = Region.objects.filter(pk=pk).first() if pk else None
        form = RegionForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, _("Region saved."))
            return redirect("dashboard:regions")
    else:
        form = RegionForm()
    return render(request, "dashboard/regions.html", {
        "active_nav": "regions", "form": form, "regions": Region.objects.all(),
    })


@staff_required
def region_delete(request, pk):
    if request.method == "POST":
        try:
            Region.objects.get(pk=pk).delete()
            messages.success(request, _("Region deleted."))
        except Exception:
            messages.error(request, _("Cannot delete a region that still has orders."))
    return redirect("dashboard:regions")


# ---------- Orders ----------
@staff_required
def orders(request):
    qs = Order.objects.select_related("region").prefetch_related("items").order_by("-created_at")
    status_filter = request.GET.get("status", "")
    if status_filter in OrderStatus.values:
        qs = qs.filter(status=status_filter)
    q = request.GET.get("q", "").strip()
    if q:
        flt = Q(receiver_name__icontains=q) | Q(receiver_phone__icontains=q)
        if q.isdigit():
            flt |= Q(pk=int(q))
        qs = qs.filter(flt)

    from django.core.paginator import Paginator
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    return render(request, "dashboard/orders_list.html", {
        "active_nav": "orders", "page_obj": page, "orders": page.object_list,
        "statuses": OrderStatus.choices, "status_filter": status_filter, "q": q,
    })


@staff_required
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.select_related("region", "user").prefetch_related("items"), pk=pk
    )
    return render(request, "dashboard/order_detail.html", {
        "active_nav": "orders", "order": order, "statuses": OrderStatus.choices,
    })
