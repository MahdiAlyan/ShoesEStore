"""Final DoD end-to-end: guest browse -> add to cart -> signup -> cart merged ->
checkout COD -> order visible in dashboard -> WhatsApp link correct & bilingual ->
status -> CONFIRMED -> visible in My Orders. Verified in EN and AR."""
from decimal import Decimal

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.utils import translation


class FinalDoDTests(TestCase):
    def setUp(self):
        cache.clear()
        translation.activate("en")
        call_command("seed_demo", verbosity=0)

    def _first_in_stock_variant(self):
        from apps.catalog.models import ProductVariant
        return ProductVariant.objects.filter(stock__gte=3).select_related("product").first()

    def _run_flow(self, lang_prefix, email):
        from apps.orders.models import Order, OrderStatus
        c = self.client
        variant = self._first_in_stock_variant()
        stock_before = variant.stock

        # 1. Guest browses
        self.assertEqual(c.get(lang_prefix + "/products/").status_code, 200)
        # 2. Guest adds to cart
        r = c.post("/api/cart/items/", {"variant_id": variant.id, "quantity": 2}, content_type="application/json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["item_count"], 2)
        # 3. Signup (cart should merge on login)
        r = c.post(lang_prefix + "/accounts/signup/", {
            "email": email, "first_name": "E2E", "last_name": "User",
            "password1": "Str0ngPass!23", "password2": "Str0ngPass!23",
        })
        self.assertEqual(r.status_code, 302)
        # 4. Cart merged -> still 2 items for the logged-in user
        self.assertEqual(c.get("/api/cart/").json()["item_count"], 2)
        # 5. Checkout COD
        region_id = __import__("apps.orders.models", fromlist=["Region"]).Region.objects.first().id
        r = c.post(lang_prefix + "/orders/checkout/", {
            "receiver_name": "Receiver Person", "receiver_phone": "03445566",
            "region": region_id, "address": "Bldg 7, Street 3", "payment_method": "COD",
        })
        self.assertEqual(r.status_code, 302, "checkout should redirect to success")
        order = Order.objects.filter(receiver_name="Receiver Person").latest("created_at")
        self.assertEqual(order.status, OrderStatus.PENDING)
        # stock decremented
        variant.refresh_from_db()
        self.assertEqual(variant.stock, stock_before - 2)
        # 6. Order visible in dashboard (admin)
        admin = __import__("django.contrib.auth", fromlist=["get_user_model"]).get_user_model()
        admin_user = admin.objects.get(email="admin@shoestore.local")
        admin_client = self.client_class()
        admin_client.force_login(admin_user)
        self.assertContains(admin_client.get(lang_prefix + "/dashboard/orders/"), "Receiver Person")
        # 7. WhatsApp link correct + bilingual
        wl = admin_client.get(f"/api/admin/orders/{order.pk}/whatsapp-link/").json()["url"]
        self.assertTrue(wl.startswith("https://wa.me/9613445566?text="), wl)  # single 0 stripped, +961 added
        from urllib.parse import unquote
        msg = unquote(wl.split("text=", 1)[1])
        self.assertIn(f"Order #{order.pk} — ShoeStore", msg)
        self.assertIn("Please reply to CONFIRM your order.", msg)
        self.assertIn("الرجاء الرد لتأكيد الطلب.", msg)  # bilingual
        self.assertIn(f"Total: ${order.total:.2f}", msg)
        # 8. Status -> CONFIRMED via admin AJAX
        r = admin_client.patch(f"/api/admin/orders/{order.pk}/status/",
                               {"status": "CONFIRMED"}, content_type="application/json")
        self.assertEqual(r.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.CONFIRMED)
        # 9. Visible in customer's My Orders
        self.assertContains(c.get(lang_prefix + "/orders/mine/"), f"#{order.pk}")
        return msg

    def test_full_flow_english(self):
        msg = self._run_flow("", "e2e_en@test.com")
        self.assertIn("- ", msg)  # at least one item line

    def test_full_flow_arabic(self):
        self._run_flow("/ar", "e2e_ar@test.com")
