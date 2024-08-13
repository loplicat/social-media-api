import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from content.upload_image_to import UploadToPath


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, related_name="profile", on_delete=models.CASCADE
    )
    profile_image = models.ImageField(
        null=False, upload_to=UploadToPath("profile_image/"), default="default.jpg"
    )
    username = models.CharField(
        max_length=100, unique=True, default="user" + str(uuid.uuid4())
    )
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    bio = models.CharField(max_length=200, null=True, blank=True)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return self.username


User = get_user_model()


@receiver(post_save, sender=User)
def create_user_profile_post_save(sender, instance, created, *args, **kwargs):
    if created:
        Profile.objects.create(user=instance)
