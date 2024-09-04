from django.urls import path, include
from rest_framework import routers

from content.views import (
    CurrentUserProfileView,
    ProfileViewSet,
    FollowersView,
    FollowingView,
    PostViewSet,
    CommentViewSet,
)

router = routers.DefaultRouter()

router.register("profiles", ProfileViewSet)
router.register("posts", PostViewSet)
router.register(r"posts/(?P<post_id>\d+)/comments", CommentViewSet, "post-comments")

urlpatterns = [
    path("", include(router.urls)),
    path("me/", CurrentUserProfileView.as_view(), name="me"),
    path("me/followers/", FollowersView.as_view(), name="me_followers"),
    path("me/following/", FollowingView.as_view(), name="me_following"),
]

app_name = "content"
