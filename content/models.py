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
    username = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
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


class Follow(models.Model):
    follower = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="following"
    )
    following = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="followers"
    )

    def __str__(self):
        return f"{self.follower} follows {self.following}"

    class Meta:
        unique_together = (("follower", "following"),)


class Hashtag(models.Model):
    title = models.CharField(max_length=100, verbose_name="Hashtag")

    def __str__(self):
        return self.title


class Post(models.Model):
    author = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="posts")
    pub_date = models.DateTimeField(auto_now_add=True)
    schedule_date = models.DateTimeField(null=True, blank=True, default=None)
    image = models.ImageField(upload_to=UploadToPath(f"posts/"), null=True, blank=True)
    text = models.TextField(max_length=500, default="")
    hashtags = models.ManyToManyField(Hashtag, blank=True, related_name="posts")

    def __str__(self):
        return f"{self.author}'s post created at {self.pub_date}"

    def get_comments(self):
        return Comment.objects.filter(post_id=self.pk)

    def get_comments_count(self):
        return Comment.objects.filter(post=self.pk).count()

    class Meta:
        ordering = ["-pub_date"]


class PostLike(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    liked_by = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="likes"
    )
    liked_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.liked_by} liked {self.post}"

    class Mets:
        unique_together = (("profile", "post"),)
        ordering = ["-liked_at"]


class Comment(models.Model):
    author = models.ForeignKey(Profile, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    commented_at = models.DateTimeField(auto_now_add=True)
    text = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.author} commented at {self.commented_at}: {self.text}"

    class Meta:
        ordering = ["-commented_at"]
