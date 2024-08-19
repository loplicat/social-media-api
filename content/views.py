from django.db.models import Count, Exists, OuterRef
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.generics import (
    RetrieveUpdateDestroyAPIView,
    get_object_or_404,
    ListAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from content.models import Profile, Follow, Post, PostLike, Comment
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
    CommentSerializer,
    PostLikeSerializer,
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
        if self.action in ("follow", "unfollow"):
            self.serializer_class = FollowerSerializer
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

        username = self.request.query_params.get("username")
        if username:
            queryset = queryset.filter(username__iexact=username)

        first_name = self.request.query_params.get("first_name")
        if first_name:
            queryset = queryset.filter(first_name__iexact=first_name)

        last_name = self.request.query_params.get("last_name")
        if last_name:
            queryset = queryset.filter(last_name__iexact=last_name)
        return queryset

    @action(
        methods=["POST"],
        detail=True,
        url_path="follow",
    )
    def follow(self, request, pk=None):
        follower = get_object_or_404(Profile, user=self.request.user)
        following = get_object_or_404(Profile, pk=pk)

        if follower == following:
            return Response(
                {"detail": "You cannot follow yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if Follow.objects.filter(follower=follower, following=following).exists():
            return Response(
                {"detail": "You are already following this user."},
                status=status.HTTP_409_CONFLICT,
            )

        Follow.objects.create(follower=follower, following=following)
        return Response(
            {"detail": "You started following this user."},
            status=status.HTTP_204_NO_CONTENT,
        )

    @action(
        methods=["POST"],
        detail=True,
        url_path="unfollow",
    )
    def unfollow(self, request, pk=None):
        follower = get_object_or_404(Profile, user=self.request.user)
        following = get_object_or_404(Profile, pk=pk)

        try:
            subscription = Follow.objects.get(follower=follower, following=following)
            subscription.delete()
            return Response(
                {"detail": "You unfollowed this user."},
                status=status.HTTP_204_NO_CONTENT,
            )
        except Follow.DoesNotExist:
            return Response(
                {"detail": "You are not following this user."},
                status=status.HTTP_404_NOT_FOUND,
            )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "username",
                type=OpenApiTypes.STR,
                description="Search profiles by username (ex. ?username=john)",
            ),
            OpenApiParameter(
                "first_name",
                type=OpenApiTypes.STR,
                description="Filter by first name" "name (ex. ?first_name=John)",
            ),
            OpenApiParameter(
                "last_name",
                type=OpenApiTypes.STR,
                description="Filter by last name" "name (ex. ?last_name=Doe)",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        """Get list of profiles."""
        return super().list(request, *args, **kwargs)


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
        if self.action in ("like", "unlike"):
            self.serializer_class = PostLikeSerializer
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

        hashtags = self.request.query_params.get("hashtags")
        if hashtags:
            queryset = queryset.filter(
                hashtags__title__in=hashtags.strip("/").split(",")
            )
        return queryset

    @action(
        methods=["POST"],
        detail=True,
        url_path="like",
        permission_classes=[IsAuthenticated],
    )
    def like(self, request, pk=None):
        post = get_object_or_404(Post, pk=pk)
        user_profile = self.request.user.profile
        if PostLike.objects.filter(liked_by=user_profile, post=post).exists():
            return Response(
                {"detail": "You already liked this post."},
                status=status.HTTP_409_CONFLICT,
            )
        PostLike.objects.create(liked_by=user_profile, post=post)
        return Response(
            {"detail": "You liked this post."},
            status=status.HTTP_204_NO_CONTENT,
        )

    @action(
        methods=["POST"],
        detail=True,
        url_path="unlike",
        permission_classes=[IsAuthenticated],
    )
    def unlike(self, request, pk=None):
        post = get_object_or_404(Post, pk=pk)
        user_profile = self.request.user.profile
        try:
            like = PostLike.objects.get(liked_by=user_profile, post=post)
            like.delete()
            return Response(
                {"detail": "You unliked this post."},
                status=status.HTTP_204_NO_CONTENT,
            )
        except PostLike.DoesNotExist:
            return Response(
                {"detail": "You already unliked this post."},
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(
        methods=["GET"],
        detail=False,
        url_path="my-posts",
    )
    def my_posts(self, request):
        """Endpoint to get all posts of the user."""
        user_profile = request.user.profile
        queryset = self.get_queryset().filter(author=user_profile)
        serializer = PostListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(
        methods=["GET"],
        detail=False,
        url_path="feed",
    )
    def feed(self, request):
        """Endpoint to get all posts from followed users"""
        user_profile = request.user.profile
        followed_profiles = user_profile.following.values_list("following", flat=True)
        queryset = self.get_queryset().filter(author__in=followed_profiles)
        serializer = PostListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(
        methods=["GET"],
        detail=False,
        url_path="liked",
    )
    def liked(self, request):
        """Endpoint to get all posts liked by the user"""
        user_profile = request.user.profile
        queryset = self.get_queryset().filter(likes__liked_by=user_profile)
        serializer = PostListSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "hashtags",
                type={"type": "list", "items": {"type": "string"}},
                description="Filter by hashtags titles (ex. ?hashtags=django,python)",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        """Get list of posts."""
        return super().list(request, *args, **kwargs)


class CommentViewSet(ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated, IsAuthorOrReadOnly]

    def get_queryset(self):
        queryset = Comment.objects.select_related("author", "post").filter(
            post_id=self.kwargs["post_id"]
        )
        return queryset

    def perform_create(self, serializer):
        post = get_object_or_404(Post, id=self.kwargs.get("post_id"))
        serializer.save(author=self.request.user.profile, post=post)
