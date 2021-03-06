from django.db import models
from apps.common.behaviors import Uploadable, Timestampable

ACCEPTED_FILE_TYPES = ['jpg', 'gif', 'png']


class Image(Uploadable, Timestampable):

    thumbnail_url = models.URLField(default="", blank=True)

    # MODEL PROPERTIES
    @property
    def width(self):
        if self.is_image:
            return self.meta_data.get('width') if self.meta_data.get(
                'meta') else None

    @property
    def height(self):
        if self.is_image:
            return self.meta_data.get('height') if self.meta_data.get(
                'meta') else None
