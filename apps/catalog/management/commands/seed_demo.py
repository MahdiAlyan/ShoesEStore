"""Seed demo data so the app never starts from an empty screen.

Idempotent: safe to run repeatedly (uses natural keys / get_or_create).
Creates: 1 admin, 3 categories, 4 colors, 6 sizes, 8 products with full variant
matrices + placeholder images, 5 regions, and 2 sample orders.

    python manage.py seed_demo
"""
import io
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.cart.models import Cart
from apps.catalog.models import Category, Color, Product, ProductImage, ProductVariant, Size
from apps.orders.models import Order, OrderStatus, PaymentMethod, Region
from apps.orders.services import change_status, create_order

User = get_user_model()

ADMIN_EMAIL = "admin@shoestore.local"
ADMIN_PASSWORD = "ShoeAdmin!2025"  # documented in README; rotate before real launch
CUSTOMER_EMAIL = "customer@shoestore.local"
CUSTOMER_PASSWORD = "ShoeCustomer!2025"


def make_placeholder_image(label, hex_color):
    """Generate a simple solid-color PNG with a label. Returns ContentFile or None."""
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return None
    try:
        color = hex_color.lstrip("#")
        rgb = tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:
        rgb = (120, 120, 130)
    img = Image.new("RGB", (600, 600), rgb)
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 20, 580, 580], outline=(255, 255, 255), width=4)
    draw.text((40, 280), label[:22], fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return ContentFile(buf.getvalue())


class Command(BaseCommand):
    help = "Seed demo data (admin, catalog, regions, sample orders)."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Seeding demo data...")

        admin, created = User.objects.get_or_create(
            email=ADMIN_EMAIL,
            defaults={"first_name": "Store", "last_name": "Admin", "is_staff": True, "is_superuser": True},
        )
        if created:
            admin.set_password(ADMIN_PASSWORD)
            admin.save()

        customer, c_created = User.objects.get_or_create(
            email=CUSTOMER_EMAIL, defaults={"first_name": "Sample", "last_name": "Buyer"},
        )
        if c_created:
            customer.set_password(CUSTOMER_PASSWORD)
            customer.save()

        # Categories
        cats = {}
        for slug, en, ar in [
            ("sneakers", "Sneakers", "أحذية رياضية"),
            ("boots", "Boots", "أحذية طويلة"),
            ("sandals", "Sandals", "صنادل"),
        ]:
            cats[slug] = Category.objects.get_or_create(
                slug=slug, defaults={"name_en": en, "name_ar": ar})[0]

        # Colors
        colors = {}
        for en, ar, hexc in [
            ("Black", "أسود", "#1b1b29"), ("White", "أبيض", "#e8e8ee"),
            ("Red", "أحمر", "#e74c3c"), ("Blue", "أزرق", "#3498db"),
        ]:
            colors[en] = Color.objects.get_or_create(
                name_en=en, defaults={"name_ar": ar, "hex_code": hexc})[0]

        # Sizes
        sizes = []
        for i, val in enumerate(["39", "40", "41", "42", "43", "44"], start=1):
            sizes.append(Size.objects.get_or_create(value=val, defaults={"sort_order": i})[0])

        # Regions
        for en, ar, fee in [
            ("Beirut", "بيروت", "3.00"), ("Mount Lebanon", "جبل لبنان", "4.00"),
            ("North", "الشمال", "6.00"), ("South", "الجنوب", "6.00"),
            ("Bekaa", "البقاع", "7.00"),
        ]:
            Region.objects.get_or_create(name_en=en, defaults={"name_ar": ar, "delivery_fee": Decimal(fee)})

        # Products (8)
        products_spec = [
            ("sneakers", "Runner Pro", "رَنَر برو", "45.00", ["Black", "White", "Red"]),
            ("sneakers", "Street Classic", "ستريت كلاسيك", "55.00", ["White", "Blue"]),
            ("sneakers", "Air Flex", "إير فليكس", "65.00", ["Black", "Blue"]),
            ("boots", "Trail Boot", "حذاء المسارات", "89.00", ["Black", "Red"]),
            ("boots", "Winter Warm", "دفء الشتاء", "99.00", ["Black", "White"]),
            ("boots", "Desert Boot", "حذاء الصحراء", "79.00", ["Red", "Blue"]),
            ("sandals", "Summer Slide", "صيفي منزلق", "25.00", ["White", "Blue"]),
            ("sandals", "Beach Walk", "مشية الشاطئ", "29.00", ["Black", "Red"]),
        ]

        made_products = []
        for idx, (cat, en, ar, price, color_names) in enumerate(products_spec):
            slug = en.lower().replace(" ", "-")
            product, p_created = Product.objects.get_or_create(
                slug=slug,
                defaults={
                    "category": cats[cat], "name_en": en, "name_ar": ar,
                    "description_en": f"A comfortable {en} for everyday wear.",
                    "description_ar": "حذاء مريح للاستخدام اليومي.",
                    "base_price": Decimal(price), "is_active": True,
                },
            )
            made_products.append(product)
            if not p_created:
                continue

            # One placeholder image per color (drives the gallery's color filter);
            # the first color's image is the main image.
            for ci, cname in enumerate(color_names):
                color = colors[cname]
                content = make_placeholder_image(f"{en} - {cname}", color.hex_code)
                if content:
                    pi = ProductImage(product=product, color=color, is_main=(ci == 0))
                    pi.image.save(f"{slug}-{color.id}.png", content, save=True)

            # Variant matrix: colors x sizes, varied stock (some low, some zero)
            for ci, cname in enumerate(color_names):
                for si, size in enumerate(sizes):
                    stock = (idx + ci + si) % 12  # 0..11 -> some zero, some low, some high
                    ProductVariant.objects.get_or_create(
                        product=product, color=colors[cname], size=size,
                        defaults={
                            "sku": f"{slug[:8].upper()}-{colors[cname].id}-{size.value}",
                            "stock": stock,
                        },
                    )

        # Two sample orders (exercise the real order-creation path)
        region = Region.objects.order_by("delivery_fee").first()
        if not Order.objects.filter(user=customer).exists():
            self._sample_order(customer, region, made_products, ["Black", "White"], confirm=True)
            self._sample_order(customer, region, made_products, ["Red"], confirm=False)

        self.stdout.write(self.style.SUCCESS(
            "Demo data ready.\n"
            f"  Admin:    {ADMIN_EMAIL} / {ADMIN_PASSWORD}\n"
            f"  Customer: {CUSTOMER_EMAIL} / {CUSTOMER_PASSWORD}"
        ))

    def _sample_order(self, customer, region, products, color_names, confirm):
        """Add a couple of in-stock variants to a cart and place an order."""
        cart, _ = Cart.objects.get_or_create(user=customer)
        cart.items.all().delete()
        added = 0
        for product in products:
            variant = (
                product.variants.filter(stock__gte=2, color__name_en__in=color_names)
                .select_related("color", "size").first()
            )
            if variant:
                cart.items.create(variant=variant, quantity=1)
                added += 1
            if added >= 2:
                break
        if added == 0:
            return
        order = create_order(
            user=customer, receiver_name="Sample Buyer", receiver_phone="+9613112233",
            region=region, address="Demo Street, Building 4, Floor 2",
            payment_method=PaymentMethod.COD, cart=cart,
        )
        if confirm:
            change_status(order, OrderStatus.CONFIRMED)
