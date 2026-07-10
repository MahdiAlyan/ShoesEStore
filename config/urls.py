"""Root URL configuration for ShoeStore."""
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

# Non-translated URLs: Django admin escape hatch, language switcher, API.
urlpatterns = [
    path("dj-admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("api/", include("config.api")),
]

# Translated URLs (locale prefix added by LocaleMiddleware).
urlpatterns += i18n_patterns(
    path("", include("apps.catalog.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("cart/", include("apps.cart.urls")),
    path("orders/", include("apps.orders.urls")),
    path("admin/", include("apps.dashboard.urls")),
    prefix_default_language=False,
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = "apps.catalog.views.handler404"
handler500 = "apps.catalog.views.handler500"
