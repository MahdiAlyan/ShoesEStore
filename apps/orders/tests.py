from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from apps.catalog.tests import CatalogTestData
from apps.cart.models import Cart

from .models import Order, OrderStatus, PaymentMethod, Region
from .phone import normalize_phone, wa_digits
from .services import InsufficientStock, change_status, create_order
from .whatsapp import build_whatsapp_message, build_whatsapp_url

User = get_user_model()


def make_region(fee="5.00"):
    return Region.objects.create(name_en="Beirut", name_ar="بيروت", delivery_fee=Decimal(fee))


class PhoneTests(TestCase):
    def test_normalize_prepends_country_code(self):
        self.assertEqual(normalize_phone("03123456"), "+9613123456")  # leading 0 stripped

    def test_normalize_keeps_plus(self):
        self.assertEqual(normalize_phone("+961 3 123 456"), "+9613123456")

    def test_wa_digits_strips_plus(self):
        self.assertEqual(wa_digits("+9613123456"), "9613123456")


class OrderServiceTests(TestCase):
    def setUp(self):
        self.d = CatalogTestData.build()
        self.red40 = self.d["p"].variants.get(sku="R-RED-40")  # stock 5, price 50
        self.region = make_region("5.00")
        self.user = User.objects.create_user(email="buyer@test.com", password="Str0ngPass!23")
        self.cart = Cart.objects.create(user=self.user)

    def _order(self, qty=2):
        self.cart.items.create(variant=self.red40, quantity=qty)
        return create_order(
            user=self.user, receiver_name="Ali", receiver_phone="+9613111222",
            region=self.region, address="Somewhere 12", payment_method=PaymentMethod.COD,
            cart=self.cart,
        )

    def test_order_decrements_stock_atomically(self):
        order = self._order(qty=2)
        self.red40.refresh_from_db()
        self.assertEqual(self.red40.stock, 3)  # 5 - 2
        self.assertEqual(order.status, OrderStatus.PENDING)

    def test_total_is_items_plus_region_fee_snapshot(self):
        order = self._order(qty=2)
        self.assertEqual(order.subtotal, Decimal("100.00"))  # 2 * 50
        self.assertEqual(order.delivery_fee, Decimal("5.00"))
        self.assertEqual(order.total, Decimal("105.00"))
        # snapshot survives a later region fee change
        self.region.delivery_fee = Decimal("99.00")
        self.region.save()
        order.refresh_from_db()
        self.assertEqual(order.total, Decimal("105.00"))

    def test_cart_cleared_after_order(self):
        self._order()
        self.assertEqual(self.cart.items.count(), 0)

    def test_insufficient_stock_rejected_and_named(self):
        self.cart.items.create(variant=self.red40, quantity=99)
        with self.assertRaises(InsufficientStock) as ctx:
            create_order(
                user=self.user, receiver_name="Ali", receiver_phone="+9613111222",
                region=self.region, address="X", payment_method=PaymentMethod.COD, cart=self.cart,
            )
        self.assertIn("Runner", str(ctx.exception))
        self.red40.refresh_from_db()
        self.assertEqual(self.red40.stock, 5)  # unchanged

    def test_cancel_restocks(self):
        order = self._order(qty=2)
        self.red40.refresh_from_db()
        self.assertEqual(self.red40.stock, 3)
        ok, err = change_status(order, OrderStatus.CANCELLED)
        self.assertTrue(ok)
        self.red40.refresh_from_db()
        self.assertEqual(self.red40.stock, 5)  # restocked

    def test_invalid_transition_rejected(self):
        order = self._order()
        ok, err = change_status(order, OrderStatus.DELIVERED)  # PENDING -> DELIVERED not allowed
        self.assertFalse(ok)

    def test_first_order_number_is_1000_and_sequences(self):
        first = self._order(qty=1)  # clears the cart after creating the order
        self.assertEqual(first.order_number, 1000)
        second = self._order(qty=1)  # reuse the (now empty) cart
        self.assertEqual(second.order_number, 1001)

    def test_order_number_starts_above_existing_max(self):
        # Simulate a legacy/backfilled order already at 1005.
        Order.objects.filter(pk=self._order(qty=1).pk).update(order_number=1005)
        nxt = self._order(qty=1)
        self.assertEqual(nxt.order_number, 1006)


class WhatsAppTests(TestCase):
    def setUp(self):
        self.d = CatalogTestData.build()
        self.red40 = self.d["p"].variants.get(sku="R-RED-40")
        self.region = make_region("5.00")
        self.user = User.objects.create_user(email="b@test.com", password="Str0ngPass!23")
        self.cart = Cart.objects.create(user=self.user)
        self.cart.items.create(variant=self.red40, quantity=2)
        self.order = create_order(
            user=self.user, receiver_name="Ali", receiver_phone="+9613111222",
            region=self.region, address="X", payment_method=PaymentMethod.COD, cart=self.cart,
        )

    def test_message_structure_and_bilingual_line(self):
        msg = build_whatsapp_message(self.order)
        self.assertIn(f"Order #{self.order.order_number} — ShoeStore", msg)
        self.assertIn("Please reply to CONFIRM your order.", msg)
        self.assertIn("الرجاء الرد لتأكيد الطلب.", msg)  # bilingual
        self.assertIn("Total: $105.00", msg)
        self.assertIn("- Runner | Red | Size 40 x2 — $100.00", msg)

    def test_url_encodes_and_strips_plus(self):
        url = build_whatsapp_url(self.order)
        self.assertTrue(url.startswith("https://wa.me/9613111222?text="))
        self.assertNotIn(" ", url)  # spaces urlencoded


class CheckoutFlowTests(TestCase):
    def setUp(self):
        cache.clear()
        self.d = CatalogTestData.build()
        self.red40 = self.d["p"].variants.get(sku="R-RED-40")  # stock 5
        self.region = make_region("5.00")
        self.user = User.objects.create_user(email="buyer@test.com", password="Str0ngPass!23")

    def _add_to_cart(self, qty=2):
        self.client.post(
            "/api/cart/items/", {"variant_id": self.red40.id, "quantity": qty},
            content_type="application/json",
        )

    def test_checkout_requires_login(self):
        resp = self.client.get(reverse("orders:checkout"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp["Location"])

    def test_happy_path_cod(self):
        self._add_to_cart(2)
        self.client.force_login(self.user)
        resp = self.client.post(reverse("orders:checkout"), {
            "receiver_name": "Ali", "receiver_phone": "03999888",
            "region": self.region.id, "address": "Street 1", "payment_method": "COD",
        })
        self.assertEqual(resp.status_code, 302)
        order = Order.objects.get(user=self.user)
        self.assertIn(reverse("orders:success", kwargs={"pk": order.pk}), resp["Location"])
        self.assertEqual(order.total, Decimal("105.00"))
        self.red40.refresh_from_db()
        self.assertEqual(self.red40.stock, 3)
        self.assertEqual(order.receiver_phone, "+9613999888")  # normalized (leading 0 stripped)

    def test_online_payment_bounces_to_checkout_without_order(self):
        # M3: ONLINE is handled by the checkout modal (reverts to COD). The
        # server-side guard never creates an ONLINE order — it bounces back to
        # checkout. The old static /payment/online/ route is removed.
        self._add_to_cart(1)
        self.client.force_login(self.user)
        resp = self.client.post(reverse("orders:checkout"), {
            "receiver_name": "Ali", "receiver_phone": "03999888",
            "region": self.region.id, "address": "Street 1", "payment_method": "ONLINE",
        })
        self.assertRedirects(resp, reverse("orders:checkout"))
        self.assertFalse(Order.objects.filter(user=self.user).exists())

    def test_api_order_create_and_list_mine(self):
        self._add_to_cart(2)
        self.client.force_login(self.user)
        resp = self.client.post("/api/orders/", {
            "receiver_name": "Ali", "receiver_phone": "+9613999888",
            "region_id": self.region.id, "address": "Street 1", "payment_method": "COD",
        }, content_type="application/json")
        self.assertEqual(resp.status_code, 201)
        oid = resp.json()["id"]
        listing = self.client.get("/api/orders/")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.json()), 1)
        self.assertEqual(listing.json()[0]["id"], oid)

    def test_api_order_create_requires_auth(self):
        self._add_to_cart(1)
        resp = self.client.post("/api/orders/", {
            "receiver_name": "Ali", "receiver_phone": "+9613999888",
            "region_id": self.region.id, "address": "Street 1", "payment_method": "COD",
        }, content_type="application/json")
        self.assertEqual(resp.status_code, 403)

    def test_pages_load_both_languages(self):
        self._add_to_cart(1)
        self.client.force_login(self.user)
        # reverse() yields the unprefixed (English) path; prepend /ar for Arabic.
        for path in ["/orders/checkout/", "/orders/mine/"]:
            self.assertEqual(self.client.get(path).status_code, 200, path)
            self.assertEqual(self.client.get("/ar" + path).status_code, 200, "/ar" + path)
