from django.db.models import Count, Exists, OuterRef
from rest_framework import mixins
from rest_framework.generics import (
    RetrieveUpdateDestroyAPIView,
    get_object_or_404,
    ListAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from content.models import Profile, Follow, Post, PostLike
from content.permissions import IsAuthorOrReadOnly
from content.serializers import (
    ProfileSerializer,
    ProfileListSerializer,
    ProfileDetailSerializer,
    FollowerSerializer,
    FollowingSerializer,
    PostSerializer,
    PostListSerializer,
    PostDetailListSerializer,
)


class CurrentUserProfileView(RetrieveUpdateDestroyAPIView):
    serializer_class = ProfileSerializer

    def get_queryset(self):
        return Profile.objects.filter(user=self.request.user).annotate(
            followers_count=Count("followers"), following_count=Count("following")
        )

    def get_object(self):
        return get_object_or_404(self.get_queryset())

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        user = instance.user
        response = super().destroy(request, *args, **kwargs)
        user.delete()
        return response


class ProfileViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet,
):
    serializer_class = ProfileSerializer
    queryset = Profile.objects.all()

    def get_serializer_class(self):
        if self.action == "list":
            self.serializer_class = ProfileListSerializer
        if self.action == "retrieve":
            self.serializer_class = ProfileDetailSerializer
        return self.serializer_class

    def get_queryset(self):
        queryset = Profile.objects.annotate(
            is_followed_by_me=Exists(
                Follow.objects.filter(
                    follower__user=self.request.user, following=OuterRef("pk")
                )
            ),
            followers_count=Count("followers"),
            following_count=Count("following"),
        )
        return queryset


class FollowersView(ListAPIView):
    serializer_class = FollowerSerializer

    def get_queryset(self):
        user = self.request.user
        return user.profile.followers.all()


class FollowingView(ListAPIView):
    serializer_class = FollowingSerializer

    def get_queryset(self):
        user = self.request.user
        return user.profile.following.all()


class PostViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated, IsAuthorOrReadOnly]
    queryset = Post.objects.all()
    serializer_class = PostSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user.profile)

    def get_serializer_class(self):
        if self.action == "list":
            self.serializer_class = PostListSerializer
        if self.action == "retrieve":
            self.serializer_class = PostDetailListSerializer
        return self.serializer_class

    def get_queryset(self):
        user_profile = self.request.user.profile
        queryset = (
            Post.objects.select_related("author")
            .prefetch_related("hashtags")
            .annotate(
                likes_count=Count("likes"),
                comments_count=Count("comments"),
                liked_by_user=Exists(
                    PostLike.objects.filter(liked_by=user_profile, post=OuterRef("pk"))
                ),
            )
        )
        return queryset
