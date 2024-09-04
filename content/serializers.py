from django.db import transaction
from rest_framework import serializers

from content.models import Profile, Follow, Hashtag, Post, Comment, PostLike


class ProfileSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    followers_count = serializers.IntegerField(read_only=True)
    following_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Profile
        fields = (
            "id",
            "username",
            "user_email",
            "first_name",
            "last_name",
            "bio",
            "profile_image",
            "followers_count",
            "following_count",
        )


class ProfileListSerializer(ProfileSerializer):
    is_followed_by_me = serializers.BooleanField(read_only=True, default=False)

    class Meta:
        model = Profile
        fields = ("id", "username", "full_name", "profile_image", "is_followed_by_me")


class FollowerSerializer(serializers.ModelSerializer):
    profile_id = serializers.IntegerField(source="follower.id", read_only=True)
    username = serializers.CharField(source="follower.username", read_only=True)

    class Meta:
        model = Follow
        fields = ("profile_id", "username")


class FollowingSerializer(serializers.ModelSerializer):
    profile_id = serializers.IntegerField(source="following.id", read_only=True)
    username = serializers.CharField(source="following.username", read_only=True)

    class Meta:
        model = Follow
        fields = ("profile_id", "username")


class HashtagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hashtag
        fields = ("id", "title")


class CommentSerializer(serializers.ModelSerializer):
    post_id = serializers.IntegerField(source="post.id", read_only=True)
    author_username = serializers.CharField(source="author.username", read_only=True)
    commented_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Comment
        fields = ("id", "author_username", "post_id", "text", "commented_at")


class PostLikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostLike
        fields = ("id", "liked_by")
        read_only_fields = ("liked_by",)


class PostSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source="author.username", read_only=True)
    author_full_name = serializers.CharField(source="author.full_name", read_only=True)
    author_image = serializers.ImageField(source="author.profile_image", read_only=True)
    hashtags = HashtagSerializer(many=True, read_only=True)
    likes_count = serializers.IntegerField(read_only=True, default=0)
    comments_count = serializers.IntegerField(read_only=True, default=0)
    schedule_date = serializers.DateTimeField(required=False, write_only=True)

    class Meta:
        model = Post
        fields = (
            "id",
            "author_username",
            "author_full_name",
            "author_image",
            "pub_date",
            "schedule_date",
            "text",
            "image",
            "likes_count",
            "comments_count",
            "hashtags",
        )

    @staticmethod
    def determine_hashtags(post_text: str) -> set:
        hashtags = set(
            post_word.strip("#")
            for post_word in post_text.split()
            if post_word.startswith("#")
        )
        return hashtags

    def create(self, validated_data):
        with transaction.atomic():
            post = Post.objects.create(**validated_data)
            post_text = validated_data.pop("text")
            hashtags_data = self.determine_hashtags(post_text)
            posts_hashtags = []
            for hashtag in hashtags_data:
                hashtag, created = Hashtag.objects.get_or_create(title=hashtag)
                posts_hashtags.append(hashtag.id)
            post.hashtags.add(*posts_hashtags)
            return post


class PostListSerializer(PostSerializer):
    liked_by_user = serializers.BooleanField(read_only=True, default=False)

    class Meta:
        model = Post
        fields = PostSerializer.Meta.fields + ("liked_by_user",)


class PostDetailListSerializer(PostListSerializer):
    comments = CommentSerializer(many=True, read_only=True)
    likes = PostLikeSerializer(many=True, read_only=True)

    class Meta:
        model = Post
        fields = PostListSerializer.Meta.fields + ("comments", "likes")


class PostInProfile(PostSerializer):
    class Meta:
        model = Post
        fields = ("id", "pub_date", "text", "image", "likes_count", "comments_count")


class ProfileDetailSerializer(ProfileListSerializer):
    followers_count = serializers.IntegerField()
    following_count = serializers.IntegerField()
    posts = PostInProfile(many=True, read_only=True)

    class Meta:
        model = Profile
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "bio",
            "profile_image",
            "is_followed_by_me",
            "followers_count",
            "following_count",
            "posts",
        )
