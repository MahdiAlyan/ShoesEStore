"""Seed demo data so the app never starts from an empty screen.

Idempotent: safe to run repeatedly (uses natural keys / get_or_create).
Creates: 1 admin, 3 categories, 4 colors, 6 sizes, 8 products with full variant
matrices + placeholder images, 5 regions, and 2 sample orders.

    python manage.py seed_demo            # idempotent top-up
    python manage.py seed_demo --flush    # wipe catalog/cart/orders (keep users), reseed
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


def make_placeholder_image(hex_color, size=(1000, 1000)):
    """Neutral 1:1 placeholder: light background + a centered color swatch (M8.1).

    Script-neutral by design — no text — so there are no tiny English-only labels
    on dark blocks. The swatch reflects the variant color, keeping the gallery's
    color filter demonstrable. Consistent square aspect so cards align.
    Returns a ContentFile, or None if Pillow is unavailable.
    """
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return None
    try:
        color = hex_color.lstrip("#")
        rgb = tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:
        rgb = (120, 120, 130)

    w, h = size
    bg = (238, 240, 243)  # light neutral
    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, w - 1, h - 1], outline=(220, 222, 226), width=3)

    cx, cy = w // 2, h // 2
    r = int(min(w, h) * 0.28)
    # Outer ring keeps very light swatches (e.g. White) visible on the light bg.
    draw.ellipse([cx - r - 12, cy - r - 12, cx + r + 12, cy + r + 12], outline=(205, 208, 214), width=4)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=rgb, outline=(180, 183, 190), width=4)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return ContentFile(buf.getvalue())


class Command(BaseCommand):
    help = "Seed demo data (admin, catalog, regions, sample orders)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Wipe catalog/cart/order data (NOT users) before seeding, to purge junk entries.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options.get("flush"):
            self._flush()
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

            # Ensure at least one placeholder image per color (M8.3), idempotently:
            # drives the gallery color filter; the first color's image is main.
            for ci, cname in enumerate(color_names):
                color = colors[cname]
                if product.images.filter(color=color).exists():
                    continue
                content = make_placeholder_image(color.hex_code)
                if content:
                    is_main = ci == 0 and not product.images.filter(is_main=True).exists()
                    pi = ProductImage(product=product, color=color, is_main=is_main)
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

    def _flush(self):
        """Delete catalog/cart/order data but keep user accounts (M8.2).

        Deletion order respects PROTECT FKs: orders (cascade items) → carts →
        images/variants → products → categories/colors/sizes/regions.
        """
        self.stdout.write("Flushing catalog / cart / order data (keeping users)...")
        Order.objects.all().delete()          # cascades OrderItems
        Cart.objects.all().delete()           # cascades CartItems
        ProductImage.objects.all().delete()
        ProductVariant.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()
        Color.objects.all().delete()
        Size.objects.all().delete()
        Region.objects.all().delete()

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
