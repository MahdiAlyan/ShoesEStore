from django.apps import AppConfig


class CartConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.cart"
    label = "cart"

    def ready(self):
        from django.contrib.auth.signals import user_logged_in

        from .services import merge_session_cart_on_login

        user_logged_in.connect(
            merge_session_cart_on_login, dispatch_uid="cart_merge_on_login"
        )
