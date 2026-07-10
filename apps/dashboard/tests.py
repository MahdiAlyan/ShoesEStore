from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.catalog.tests import CatalogTestData
from apps.cart.models import Cart
from apps.orders.models import Order, OrderStatus, PaymentMethod, Region
from apps.orders.services import create_order

User = get_user_model()


class DashboardData:
    @staticmethod
    def build():
        d = CatalogTestData.build()
        d["red40"] = d["p"].variants.get(sku="R-RED-40")  # stock 5
        d["region"] = Region.objects.create(name_en="Beirut", name_ar="بيروت", delivery_fee=Decimal("5.00"))
        d["admin"] = User.objects.create_user(email="admin@test.com", password="x", is_staff=True)
        d["customer"] = User.objects.create_user(email="cust@test.com", password="x")
        cart = Cart.objects.create(user=d["customer"])
        cart.items.create(variant=d["red40"], quantity=2)
        d["order"] = create_order(
            user=d["customer"], receiver_name="Ali", receiver_phone="+9613111222",
            region=d["region"], address="X", payment_method=PaymentMethod.COD, cart=cart,
        )
        return d


class DashboardAccessTests(TestCase):
    def setUp(self):
        self.d = DashboardData.build()

    def test_non_staff_redirected_from_dashboard(self):
        self.client.force_login(self.d["customer"])
        resp = self.client.get("/dashboard/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp["Location"])

    def test_staff_can_view_pages(self):
        self.client.force_login(self.d["admin"])
        for path in ["/dashboard/", "/dashboard/products/", "/dashboard/categories/",
                     "/dashboard/regions/", "/dashboard/orders/",
                     f"/dashboard/orders/{self.d['order'].pk}/", "/dashboard/products/new/"]:
            self.assertEqual(self.client.get(path).status_code, 200, path)

    def test_pages_load_arabic(self):
        self.client.force_login(self.d["admin"])
        self.assertEqual(self.client.get("/ar/dashboard/").status_code, 200)
        self.assertEqual(self.client.get("/ar/dashboard/orders/").status_code, 200)


class AdminOrderApiTests(TestCase):
    def setUp(self):
        self.d = DashboardData.build()
        self.order = self.d["order"]
        self.red40 = self.d["red40"]

    def test_non_staff_blocked_from_admin_api(self):
        self.client.force_login(self.d["customer"])
        resp = self.client.get("/api/admin/orders/")
        self.assertEqual(resp.status_code, 403)

    def test_status_transition_confirm(self):
        self.client.force_login(self.d["admin"])
        resp = self.client.patch(
            f"/api/admin/orders/{self.order.pk}/status/",
            {"status": "CONFIRMED"}, content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.CONFIRMED)

    def test_invalid_transition_rejected(self):
        self.client.force_login(self.d["admin"])
        resp = self.client.patch(
            f"/api/admin/orders/{self.order.pk}/status/",
            {"status": "DELIVERED"}, content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_cancel_restocks_via_api(self):
        self.red40.refresh_from_db()
        self.assertEqual(self.red40.stock, 3)  # 5 - 2 at order time
        self.client.force_login(self.d["admin"])
        resp = self.client.patch(
            f"/api/admin/orders/{self.order.pk}/status/",
            {"status": "CANCELLED"}, content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.red40.refresh_from_db()
        self.assertEqual(self.red40.stock, 5)  # restocked

    def test_whatsapp_link_endpoint(self):
        self.client.force_login(self.d["admin"])
        resp = self.client.get(f"/api/admin/orders/{self.order.pk}/whatsapp-link/")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["url"].startswith("https://wa.me/9613111222?text="))

    def test_search_and_filter(self):
        self.client.force_login(self.d["admin"])
        self.assertEqual(len(self.client.get("/api/admin/orders/?status=PENDING").json()), 1)
        self.assertEqual(len(self.client.get("/api/admin/orders/?status=DELIVERED").json()), 0)
        self.assertEqual(len(self.client.get("/api/admin/orders/?q=Ali").json()), 1)
        self.assertEqual(len(self.client.get(f"/api/admin/orders/?q={self.order.pk}").json()), 1)


class BulkVariantApiTests(TestCase):
    """M6.3 — POST /api/admin/products/{id}/variants/bulk/."""

    def setUp(self):
        self.d = DashboardData.build()
        self.product = self.d["p"]  # has R-RED-40, R-RED-41, R-BLU-40 (blue×41 missing)
        self.url = f"/api/admin/products/{self.product.pk}/variants/bulk/"

    def _payload(self, **over):
        base = {
            "color_ids": [self.d["red"].id, self.d["blue"].id],
            "size_ids": [self.d["s40"].id, self.d["s41"].id],
            "stock": 7,
            "sku_prefix": "",
        }
        base.update(over)
        return base

    def test_creates_only_missing_combinations(self):
        self.client.force_login(self.d["admin"])
        before = self.product.variants.count()
        resp = self.client.post(self.url, self._payload(), content_type="application/json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json(), {"created": 1, "skipped": 3})
        self.assertEqual(self.product.variants.count(), before + 1)
        # the new variant is blue × 41 with the requested stock
        v = self.product.variants.get(color=self.d["blue"], size=self.d["s41"])
        self.assertEqual(v.stock, 7)

    def test_second_run_skips_all(self):
        self.client.force_login(self.d["admin"])
        self.client.post(self.url, self._payload(), content_type="application/json")
        resp = self.client.post(self.url, self._payload(), content_type="application/json")
        self.assertEqual(resp.json(), {"created": 0, "skipped": 4})

    def test_sku_uses_prefix_uppercased(self):
        self.client.force_login(self.d["admin"])
        self.client.post(self.url, self._payload(sku_prefix="run x"), content_type="application/json")
        v = self.product.variants.get(color=self.d["blue"], size=self.d["s41"])
        self.assertTrue(v.sku.startswith("RUN-X-"))
        self.assertEqual(v.sku, v.sku.upper())

    def test_requires_color_and_size(self):
        self.client.force_login(self.d["admin"])
        resp = self.client.post(self.url, self._payload(size_ids=[]), content_type="application/json")
        self.assertEqual(resp.status_code, 400)

    def test_non_staff_forbidden(self):
        self.client.force_login(self.d["customer"])
        resp = self.client.post(self.url, self._payload(), content_type="application/json")
        self.assertEqual(resp.status_code, 403)

    def test_anonymous_forbidden(self):
        resp = self.client.post(self.url, self._payload(), content_type="application/json")
        self.assertIn(resp.status_code, (401, 403))


class ProductCrudTests(TestCase):
    def setUp(self):
        self.d = DashboardData.build()
        self.client.force_login(self.d["admin"])

    def test_create_product_with_variant(self):
        resp = self.client.post("/dashboard/products/new/", {
            "category": self.d["cat"].id, "name_en": "Trainer", "name_ar": "مدرب",
            "slug": "trainer", "description_en": "", "description_ar": "",
            "base_price": "70.00", "is_active": "on",
            "variants-TOTAL_FORMS": "1", "variants-INITIAL_FORMS": "0",
            "variants-MIN_NUM_FORMS": "0", "variants-MAX_NUM_FORMS": "1000",
            "variants-0-color": self.d["red"].id, "variants-0-size": self.d["s40"].id,
            "variants-0-sku": "TR-RED-40", "variants-0-stock": "9",
            "images-TOTAL_FORMS": "0", "images-INITIAL_FORMS": "0",
            "images-MIN_NUM_FORMS": "0", "images-MAX_NUM_FORMS": "1000",
        })
        self.assertEqual(resp.status_code, 302)
        from apps.catalog.models import Product
        p = Product.objects.get(slug="trainer")
        self.assertEqual(p.variants.count(), 1)
        self.assertEqual(p.total_stock, 9)

    def test_invalid_variant_does_not_orphan_product(self):
        from apps.catalog.models import Product
        base = {
            "category": self.d["cat"].id, "name_en": "Ghost", "name_ar": "شبح",
            "slug": "ghost", "description_en": "", "description_ar": "",
            "base_price": "70.00", "is_active": "on",
            "variants-TOTAL_FORMS": "1", "variants-INITIAL_FORMS": "0",
            "variants-MIN_NUM_FORMS": "0", "variants-MAX_NUM_FORMS": "1000",
            # invalid: missing color/size/sku
            "variants-0-color": "", "variants-0-size": "", "variants-0-sku": "", "variants-0-stock": "5",
            "images-TOTAL_FORMS": "0", "images-INITIAL_FORMS": "0",
            "images-MIN_NUM_FORMS": "0", "images-MAX_NUM_FORMS": "1000",
        }
        resp = self.client.post("/dashboard/products/new/", base)
        self.assertEqual(resp.status_code, 200)  # re-rendered with errors
        self.assertFalse(Product.objects.filter(slug="ghost").exists())  # no orphan committed
