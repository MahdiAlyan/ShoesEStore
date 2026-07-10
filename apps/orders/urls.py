from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("checkout/", views.checkout, name="checkout"),
    path("success/<int:pk>/", views.order_success, name="success"),
    path("mine/", views.my_orders, name="my_orders"),
]
