from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.catalog.tests import CatalogTestData

from .models import Cart

User = get_user_model()


class CartAPITests(TestCase):
    def setUp(self):
        self.d = CatalogTestData.build()
        self.red40 = self.d["p"].variants.get(sku="R-RED-40")  # stock 5
        self.red41 = self.d["p"].variants.get(sku="R-RED-41")  # stock 0

    def test_add_item_creates_session_cart_and_counts(self):
        resp = self.client.post(
            "/api/cart/items/", {"variant_id": self.red40.id, "quantity": 2}, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["item_count"], 2)
        self.assertEqual(Decimal(resp.json()["subtotal"]), Decimal("100.00"))

    def test_out_of_stock_rejected(self):
        resp = self.client.post(
            "/api/cart/items/", {"variant_id": self.red41.id, "quantity": 1}, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_add_over_stock_is_rejected_and_named(self):
        resp = self.client.post(
            "/api/cart/items/", {"variant_id": self.red40.id, "quantity": 99}, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("5", resp.json()["warning"])

    def test_patch_and_delete(self):
        self.client.post(
            "/api/cart/items/", {"variant_id": self.red40.id, "quantity": 1}, content_type="application/json"
        )
        item_id = self.client.get("/api/cart/").json()["items"][0]["id"]
        r = self.client.patch(
            f"/api/cart/items/{item_id}/", {"quantity": 3}, content_type="application/json"
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["item_count"], 3)
        r = self.client.delete(f"/api/cart/items/{item_id}/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["item_count"], 0)

    def test_patch_over_stock_clamped_with_warning(self):
        self.client.post(
            "/api/cart/items/", {"variant_id": self.red40.id, "quantity": 1}, content_type="application/json"
        )
        item_id = self.client.get("/api/cart/").json()["items"][0]["id"]
        r = self.client.patch(
            f"/api/cart/items/{item_id}/", {"quantity": 50}, content_type="application/json"
        )
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["items"][0]["quantity"], 5)

    def test_cart_api_has_no_n_plus_one(self):
        from django.test.utils import CaptureQueriesContext
        from django.db import connection

        self.client.post(
            "/api/cart/items/", {"variant_id": self.red40.id, "quantity": 1}, content_type="application/json"
        )
        with CaptureQueriesContext(connection) as q1:
            self.client.get("/api/cart/")
        one_item = len(q1)

        self.client.post(
            "/api/cart/items/", {"variant_id": self.d["p"].variants.get(sku="R-BLU-40").id, "quantity": 1},
            content_type="application/json",
        )
        with CaptureQueriesContext(connection) as q2:
            resp = self.client.get("/api/cart/")
        # Query count must be constant regardless of item count (no N+1).
        self.assertEqual(one_item, len(q2))
        self.assertEqual(len(resp.json()["items"]), 2)

    def test_cart_page_renders_empty_and_with_item_both_languages(self):
        for prefix in ["", "/ar"]:
            self.assertEqual(self.client.get(prefix + "/cart/").status_code, 200)
        self.client.post(
            "/api/cart/items/", {"variant_id": self.red40.id, "quantity": 1}, content_type="application/json"
        )
        # Each language renders the product name in that language.
        self.assertContains(self.client.get("/cart/"), "Runner")
        self.assertContains(self.client.get("/ar/cart/"), "رانر")

    def test_cannot_touch_other_users_cart_item(self):
        # Item in an unrelated cart must 404 for this session.
        other = Cart.objects.create(session_key="someoneelse")
        item = other.items.create(variant=self.red40, quantity=1)
        r = self.client.patch(
            f"/api/cart/items/{item.id}/", {"quantity": 2}, content_type="application/json"
        )
        self.assertEqual(r.status_code, 404)


class CartMergeTests(TestCase):
    def setUp(self):
        self.d = CatalogTestData.build()
        self.red40 = self.d["p"].variants.get(sku="R-RED-40")  # stock 5
        self.blue40 = self.d["p"].variants.get(sku="R-BLU-40")  # stock 3
        self.user = User.objects.create_user(email="buyer@test.com", password="Str0ngPass!23")

    def test_session_cart_merges_into_user_cart_on_login(self):
        # Guest adds items
        self.client.post(
            "/api/cart/items/", {"variant_id": self.red40.id, "quantity": 2}, content_type="application/json"
        )
        # Pre-existing user cart with overlapping + distinct item
        user_cart = Cart.objects.create(user=self.user)
        user_cart.items.create(variant=self.red40, quantity=1)
        user_cart.items.create(variant=self.blue40, quantity=1)
        # Login triggers merge
        self.client.force_login(self.user)
        self.client.get("/api/cart/")  # ensure resolution
        user_cart.refresh_from_db()
        counts = {i.variant_id: i.quantity for i in user_cart.items.all()}
        # red40: 1 (user) + 2 (guest) = 3, capped at stock 5 -> 3
        self.assertEqual(counts[self.red40.id], 3)
        self.assertEqual(counts[self.blue40.id], 1)

    def test_merge_caps_at_stock(self):
        self.client.post(
            "/api/cart/items/", {"variant_id": self.blue40.id, "quantity": 2}, content_type="application/json"
        )
        user_cart = Cart.objects.create(user=self.user)
        user_cart.items.create(variant=self.blue40, quantity=2)  # stock is 3
        self.client.force_login(self.user)
        user_cart.refresh_from_db()
        self.assertEqual(user_cart.items.get(variant=self.blue40).quantity, 3)
