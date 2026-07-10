from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django_ratelimit.core import is_ratelimited

from apps.cart.services import get_cart, load_cart_with_items
from apps.common.turnstile import verify_turnstile

from .forms import CheckoutForm
from .models import Order, PaymentMethod, Region
from .services import EmptyCart, InsufficientStock, create_order


@login_required
def checkout(request):
    cart = load_cart_with_items(get_cart(request, create=False))
    items = list(cart.items.all()) if cart else []
    if not items:
        messages.info(request, _("Your cart is empty."))
        return redirect("cart:detail")

    regions = Region.objects.filter(is_active=True)
    form = CheckoutForm()

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if not verify_turnstile(request):
            messages.error(request, _("Please complete the human verification."))
        elif form.is_valid():
            data = form.cleaned_data
            # Online payment is a non-functional placeholder handled entirely by the
            # checkout modal (M3), which reverts the choice to COD before submit.
            # Server-side guard: never create an ONLINE order — bounce back to checkout.
            if data["payment_method"] == PaymentMethod.ONLINE:
                messages.info(request, _("Online payment is coming soon. Please choose Cash on Delivery."))
                return redirect("orders:checkout")
            # Rate limit only real order creation (shared bucket with the API).
            if is_ratelimited(request, group="order-create", key="user",
                              rate="10/h", method="POST", increment=True):
                messages.error(request, _("Too many orders. Please try again later."))
                return redirect("orders:checkout")
            try:
                order = create_order(
                    user=request.user,
                    receiver_name=data["receiver_name"],
                    receiver_phone=data["receiver_phone"],
                    region=data["region"],
                    address=data["address"],
                    payment_method=PaymentMethod.COD,
                    cart=cart,
                )
            except InsufficientStock as exc:
                messages.error(request, str(exc))
                return redirect("cart:detail")
            except EmptyCart:
                messages.info(request, _("Your cart is empty."))
                return redirect("cart:detail")
            # One-time success toast on the success page (M5, via messages->Swal).
            messages.success(request, _("Order #%(num)s placed! We will confirm on WhatsApp.") % {"num": order.order_number})
            return redirect("orders:success", pk=order.pk)

    context = {
        "form": form,
        "cart": cart,
        "items": items,
        "regions": regions,
    }
    return render(request, "orders/checkout.html", context)


@login_required
def order_success(request, pk):
    order = get_object_or_404(
        Order.objects.select_related("region").prefetch_related("items"),
        pk=pk, user=request.user,
    )
    return render(request, "orders/success.html", {"order": order})


@login_required
def my_orders(request):
    orders = (
        Order.objects.filter(user=request.user)
        .select_related("region")
        .prefetch_related("items")
        .order_by("-created_at")
    )
    return render(request, "orders/my_orders.html", {"orders": orders})
