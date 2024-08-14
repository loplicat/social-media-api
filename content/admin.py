from django.contrib import admin

from content.models import Profile, Post, Comment, Follow, Hashtag, PostLike

admin.site.register(Profile)
admin.site.register(Follow)
admin.site.register(Hashtag)
admin.site.register(PostLike)
admin.site.register(Post)
admin.site.register(Comment)
