from .models import Category


def nav_categories(request):
    """Categories for the storefront navbar."""
    return {"nav_categories": Category.objects.all()}
