from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from content.models import Profile, Follow, Hashtag, Post, PostLike, Comment
from content.serializers import (
    PostSerializer,
    PostListSerializer,
    ProfileListSerializer,
)

POSTS_URL = reverse("content:post-list")
PROFILES_URL = reverse("content:profile-list")

User = get_user_model()


def sample_user(**params):
    defaults = {
        "email": "testuser@example.com",
        "password": "password123",
    }
    defaults.update(params)
    return User.objects.create_user(**defaults)


def sample_post(**params):
    defaults = {
        "text": "Test post",
    }
    defaults.update(params)

    return Post.objects.create(**defaults)


class UnauthenticatedSocialMediaApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(POSTS_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedProfileViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = sample_user(email="user1@example.com", password="pass1234")
        self.client.force_authenticate(user=self.user1)
        self.user2 = sample_user(email="user2@example.com", password="pass1234")
        self.profile1 = Profile.objects.get(user=self.user1)
        self.profile2 = Profile.objects.get(user=self.user2)

    def test_retrieve_profile(self):
        url = reverse("content:profile-detail", kwargs={"pk": self.profile2.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        username = response.data["username"]

    def test_list_profiles(self):
        response = self.client.get(PROFILES_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_filter_profile_by_username(self):
        res = self.client.get(PROFILES_URL, {"username": f"{self.profile1.username}"})

        serializer1 = ProfileListSerializer(
            self.profile1, context={"request": res.wsgi_request}
        )
        serializer2 = ProfileListSerializer(
            self.profile2, context={"request": res.wsgi_request}
        )
        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_filter_profile_by_first_and_last_name(self):
        self.profile1.first_name = "Test1"
        self.profile1.save()
        self.profile2.last_name = "Test2"
        self.profile2.save()

        res = self.client.get(PROFILES_URL, {"first_name": "Test1"})

        serializer1 = ProfileListSerializer(
            self.profile1, context={"request": res.wsgi_request}
        )
        serializer2 = ProfileListSerializer(
            self.profile2, context={"request": res.wsgi_request}
        )

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

        res = self.client.get(PROFILES_URL, {"last_name": "Test2"})
        serializer1 = ProfileListSerializer(
            self.profile1, context={"request": res.wsgi_request}
        )
        serializer2 = ProfileListSerializer(
            self.profile2, context={"request": res.wsgi_request}
        )

        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer1.data, res.data)

    def test_follow_profile(self):
        url = reverse("content:profile-follow", kwargs={"pk": self.profile2.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(
            Follow.objects.filter(
                follower=self.profile1, following=self.profile2
            ).exists()
        )

    def test_unfollow_profile(self):
        Follow.objects.create(follower=self.profile1, following=self.profile2)
        url = reverse("content:profile-unfollow", kwargs={"pk": self.profile2.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            Follow.objects.filter(
                follower=self.profile1, following=self.profile2
            ).exists()
        )


class ProfileCreationTests(TestCase):
    """Auto creating profile, while create user instance, test signal."""

    def setUp(self):
        self.client = APIClient()

    def test_create_user_and_profile(self):
        user_data = {
            "email": "test@example.com",
            "password": "testpassword",
        }
        response = self.client.post(reverse("user:create"), user_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email="test@example.com").exists())

        user = User.objects.get(email="test@example.com")
        self.assertTrue(Profile.objects.filter(user=user).exists())


class AuthenticatedPostViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = sample_user(email="testuser@example.com", password="pass1234")
        self.profile = Profile.objects.get(user=self.user)
        self.post = Post.objects.create(author=self.profile, text="Test post")
        self.client.force_authenticate(user=self.user)

    def test_create_post(self):
        url = POSTS_URL
        data = {"text": "New test post #django", "author": self.profile.id}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Post.objects.count(), 2)
        self.assertEqual(Post.objects.first().text, "New test post #django")

    def test_auto_hashtag_determination(self):
        data = {
            "text": "New test post #react",
        }
        serializer = PostSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        new_post = serializer.save(author=self.profile)
        self.assertEqual(new_post.text, "New test post #react")
        self.assertEqual(new_post.hashtags.count(), 1)
        self.assertEqual(new_post.hashtags.first().title, "react")

    def test_list_posts(self):
        sample_post(author=self.profile)
        sample_post(author=self.profile)

        res = self.client.get(POSTS_URL)
        posts = Post.objects.all()
        serializer = PostListSerializer(
            posts, many=True, context={"request": res.wsgi_request}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_posts_by_hashtags(self):
        hashtag1 = Hashtag.objects.create(title="test1")
        hashtag2 = Hashtag.objects.create(title="test2")

        post1 = sample_post(author=self.profile, text="Post 1")
        post1.hashtags.add(hashtag1)
        post2 = sample_post(author=self.profile, text="Post 2")
        post2.hashtags.add(hashtag2)

        post3 = sample_post(author=self.profile, text="Post without hashtags")

        res = self.client.get(POSTS_URL, {"hashtags": f"{hashtag1},{hashtag2}"})

        serializer1 = PostListSerializer(post1, context={"request": res.wsgi_request})
        serializer2 = PostListSerializer(post2, context={"request": res.wsgi_request})
        serializer3 = PostListSerializer(post3, context={"request": res.wsgi_request})

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_retrieve_post(self):
        post = sample_post(author=self.profile)
        url = reverse("content:post-detail", args=[post.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["text"], "Test post")

    def test_like_post(self):
        url = reverse("content:post-like", kwargs={"pk": self.post.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(
            PostLike.objects.filter(post=self.post, liked_by=self.profile).exists()
        )

    def test_unlike_post(self):
        PostLike.objects.create(post=self.post, liked_by=self.profile)
        url = reverse("content:post-unlike", kwargs={"pk": self.post.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            PostLike.objects.filter(post=self.post, liked_by=self.profile).exists()
        )


class AuthenticatedCommentViewSetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = sample_user(email="testuser@example.com", password="pass12345")
        self.profile = Profile.objects.get(user=self.user)
        self.post = sample_post(author=self.profile)
        self.client.force_authenticate(user=self.user)

    def test_create_comment(self):
        url = reverse("content:post-comments-list", kwargs={"post_id": self.post.id})
        data = {"text": "Test comment"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Comment.objects.count(), 1)
        self.assertEqual(Comment.objects.first().text, "Test comment")

    def test_list_comments(self):
        Comment.objects.create(author=self.profile, post=self.post, text="Test comment")
        url = reverse("content:post-comments-list", kwargs={"post_id": self.post.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
