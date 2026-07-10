from django.contrib.auth.decorators import user_passes_test


def staff_required(view):
    """Allow only authenticated staff; others are redirected to login (?next=)."""
    return user_passes_test(lambda u: u.is_authenticated and u.is_staff)(view)
