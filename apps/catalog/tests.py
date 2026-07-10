from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .models import Category, Color, Product, ProductVariant, Size


class CatalogTestData:
    @staticmethod
    def build():
        cat = Category.objects.create(name_en="Sneakers", name_ar="أحذية رياضية", slug="sneakers")
        red = Color.objects.create(name_en="Red", name_ar="أحمر", hex_code="#e74c3c")
        blue = Color.objects.create(name_en="Blue", name_ar="أزرق", hex_code="#3498db")
        s40 = Size.objects.create(value="40", sort_order=1)
        s41 = Size.objects.create(value="41", sort_order=2)
        p = Product.objects.create(
            category=cat, name_en="Runner", name_ar="رانر", slug="runner",
            description_en="Fast", description_ar="سريع", base_price=Decimal("50.00"),
        )
        ProductVariant.objects.create(product=p, color=red, size=s40, sku="R-RED-40", stock=5)
        ProductVariant.objects.create(product=p, color=red, size=s41, sku="R-RED-41", stock=0)
        ProductVariant.objects.create(product=p, color=blue, size=s40, sku="R-BLU-40", stock=3)
        return {"cat": cat, "red": red, "blue": blue, "s40": s40, "s41": s41, "p": p}


class CatalogModelTests(TestCase):
    def setUp(self):
        self.d = CatalogTestData.build()

    def test_total_stock_and_in_stock(self):
        self.assertEqual(self.d["p"].total_stock, 8)
        self.assertTrue(self.d["p"].in_stock)

    def test_variant_shares_product_price(self):
        v = self.d["p"].variants.first()
        self.assertEqual(v.price, Decimal("50.00"))

    def test_localized_name_falls_back_to_en(self):
        from django.utils.translation import override
        with override("ar"):
            self.assertEqual(self.d["cat"].name, "أحذية رياضية")
        with override("fr"):  # unsupported language -> English fallback
            self.assertEqual(self.d["cat"].name, "Sneakers")


class CatalogViewTests(TestCase):
    def setUp(self):
        self.d = CatalogTestData.build()

    def test_list_and_detail_load_both_languages(self):
        for prefix in ["", "/ar"]:
            self.assertEqual(self.client.get(prefix + "/products/").status_code, 200)
            self.assertEqual(self.client.get(prefix + "/products/runner/").status_code, 200)

    def test_filter_by_category(self):
        resp = self.client.get(reverse("catalog:product_list"), {"category": "sneakers"})
        self.assertContains(resp, "Runner")
        resp = self.client.get(reverse("catalog:product_list"), {"category": "nonexistent"})
        self.assertNotContains(resp, "Runner")

    def test_filter_by_price_range(self):
        resp = self.client.get(reverse("catalog:product_list"), {"min_price": "100"})
        self.assertNotContains(resp, "Runner")
        resp = self.client.get(reverse("catalog:product_list"), {"max_price": "60"})
        self.assertContains(resp, "Runner")

    def test_combined_color_size_requires_matching_variant(self):
        # Runner has red/40, red/41, blue/40 — but NOT blue/41.
        resp = self.client.get(
            reverse("catalog:product_list"),
            {"color": self.d["blue"].id, "size": self.d["s41"].id},
        )
        self.assertNotContains(resp, "Runner")
        # blue/40 exists -> matches
        resp = self.client.get(
            reverse("catalog:product_list"),
            {"color": self.d["blue"].id, "size": self.d["s40"].id},
        )
        self.assertContains(resp, "Runner")

    def test_inactive_product_hidden(self):
        self.d["p"].is_active = False
        self.d["p"].save()
        self.assertEqual(self.client.get("/products/runner/").status_code, 404)


class CatalogAPITests(TestCase):
    def setUp(self):
        self.d = CatalogTestData.build()

    def test_product_list_api(self):
        resp = self.client.get("/api/products/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 1)

    def test_variant_matrix_api(self):
        resp = self.client.get("/api/products/runner/variants/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 3)
        by_sku = {v["sku"]: v for v in data}
        self.assertTrue(by_sku["R-RED-40"]["in_stock"])
        self.assertFalse(by_sku["R-RED-41"]["in_stock"])

    def test_api_color_filter(self):
        resp = self.client.get("/api/products/", {"color": self.d["blue"].id})
        self.assertEqual(resp.json()["count"], 1)
