import os
import uuid

from django.utils.deconstruct import deconstructible
from django.utils.encoding import force_str


@deconstructible
class UploadToPath(object):
    def __init__(self, upload_to):
        self.upload_to = upload_to

    def __call__(self, instance, filename):
        return self.generate_filename(filename)

    def get_directory_name(self):
        return os.path.normpath(force_str(self.upload_to))

    def get_filename(self, filename):
        _, extension = os.path.splitext(filename)
        filename = f"{uuid.uuid4()}{extension}"
        return filename

    def generate_filename(self, filename):
        return os.path.join(self.get_directory_name(), self.get_filename(filename))
