from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_image_size(image):
    """Reject uploads larger than MAX_UPLOAD_IMAGE_SIZE (5 MB)."""
    cap = getattr(settings, "MAX_UPLOAD_IMAGE_SIZE", 5 * 1024 * 1024)
    if image.size and image.size > cap:
        raise ValidationError(
            _("Image is too large (max %(mb)d MB).") % {"mb": cap // (1024 * 1024)}
        )
