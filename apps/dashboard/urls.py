from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.overview, name="overview"),
    # Products
    path("products/", views.products, name="products"),
    path("products/new/", views.product_form, name="product_create"),
    path("products/<int:pk>/edit/", views.product_form, name="product_edit"),
    path("products/<int:pk>/delete/", views.product_delete, name="product_delete"),
    # Categories
    path("categories/", views.categories, name="categories"),
    path("categories/<int:pk>/delete/", views.category_delete, name="category_delete"),
    # Regions
    path("regions/", views.regions, name="regions"),
    path("regions/<int:pk>/delete/", views.region_delete, name="region_delete"),
    # Orders
    path("orders/", views.orders, name="orders"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
]
